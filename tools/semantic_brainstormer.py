"""
Snowflake Semantic View Brainstormer.

Connects to Snowflake, introspects schemas, classifies columns, and generates:
  - generated/<view_name>.yaml        — Snowflake Semantic View YAML
  - generated/<view_name>_create.sql  — SQL to create the view + Cortex instructions

Usage:
  python -m tools.semantic_brainstormer \\
    --database ANALYTICS \\
    --schemas MART_FINANCE,MART_RISK \\
    --connection myconn \\
    [--view-name my_view] \\
    [--output-dir generated/] \\
    [--tables-filter VW_] \\
    [--create] \\
    [--verbose]
"""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from tools.column_describer import (
    DescribedColumn,
    MetricSpec,
    derive_metrics,
    describe_column,
    is_snapshot_table,
)
from tools.schema_introspector import ColumnRecord, introspect_schemas
from tools.snowconn_client import get_connection

# ── Max columns per category to keep YAML human-readable ─────────────────────
_MAX_DIMS = 30
_MAX_FACTS = 20
_MAX_TIME_DIMS = 10

# ── Snapshot keywords triggering non-additive dimension tags ──────────────────
_SNAPSHOT_FACT_SUFFIXES = (
    "_balance", "_value_usd", "_amount_usd", "_exposure",
    "_outstanding", "_price", "_rate",
)


# ── Internal model ────────────────────────────────────────────────────────────

@dataclass
class LogicalTable:
    logical_name: str
    physical_table: str
    database: str
    schema: str
    table_type: str
    description: str
    dimensions: list[DescribedColumn] = field(default_factory=list)
    time_dimensions: list[DescribedColumn] = field(default_factory=list)
    facts: list[DescribedColumn] = field(default_factory=list)
    metrics: list[MetricSpec] = field(default_factory=list)
    filters: list[dict] = field(default_factory=list)
    skipped_columns: list[str] = field(default_factory=list)
    is_snapshot: bool = False
    primary_time_dim: str | None = None


@dataclass
class Relationship:
    name: str
    left_table: str
    right_table: str
    left_column: str
    right_column: str


# ── Logical name derivation ───────────────────────────────────────────────────

def _derive_logical_name(physical: str) -> str:
    name = physical.lower()
    for prefix in ("vw_", "v_", "fact_", "dim_", "fct_", "stg_", "staging_"):
        if name.startswith(prefix):
            name = name[len(prefix):]
    return name


def _pluralize(name: str) -> str:
    if name.endswith("s"):
        return name
    if name.endswith(("x", "z", "ch", "sh")):
        return name + "es"
    return name + "s"


# ── Table assembly ────────────────────────────────────────────────────────────

def _build_logical_table(
    table_name: str,
    schema: str,
    database: str,
    table_type: str,
    table_comment: str | None,
    columns: list[ColumnRecord],
    verbose: bool,
) -> LogicalTable | None:
    logical = _derive_logical_name(table_name)
    snapshot = is_snapshot_table(table_name)

    dims: list[DescribedColumn] = []
    time_dims: list[DescribedColumn] = []
    facts: list[DescribedColumn] = []
    skipped: list[str] = []

    for col in columns:
        dc = describe_column(col, logical)
        if dc.classification == "dimension":
            dims.append(dc)
        elif dc.classification == "time_dimension":
            time_dims.append(dc)
        elif dc.classification == "fact":
            facts.append(dc)
        else:
            skipped.append(col.column)
            if verbose:
                print(
                    f"  [skip] {table_name}.{col.column} ({col.datatype})",
                    file=sys.stderr,
                )

    if not dims and not time_dims and not facts:
        print(
            f"  [warn] {table_name}: no classifiable columns — skipping.",
            file=sys.stderr,
        )
        return None

    # Choose primary time dimension for snapshot metrics
    preferred_time_names = (
        "as_of_date", "snapshot_date", "price_date", "exposure_date",
        "balance_date", "rate_date", "valuation_date",
    )
    primary_time: str | None = None
    if time_dims:
        for preferred in preferred_time_names:
            match = next((td for td in time_dims if td.name == preferred), None)
            if match:
                primary_time = match.name
                break
        if primary_time is None:
            primary_time = time_dims[0].name

    derived_metrics = derive_metrics(facts, primary_time, snapshot)
    # Always include COUNT(*)
    count_metric = MetricSpec(
        name=f"{logical}_count",
        expr="COUNT(*)",
        description=f"Count of {logical.replace('_', ' ')} records. "
                    f"Example question: 'How many {logical.replace('_', ' ')} are there?'",
    )

    # Filters: at most 2, from _status / _flag dimensions
    filters = []
    for dc in dims:
        if dc.name.endswith(("_status", "_flag")) and len(filters) < 2:
            filters.append({
                "name": f"active_{dc.name}",
                "description": f"Records where {dc.name.replace('_', ' ')} is populated.",
                "expr": f"{dc.expr} IS NOT NULL",
            })

    # Cap columns
    extra_dims = dims[_MAX_DIMS:]
    extra_facts = facts[_MAX_FACTS:]
    extra_time = time_dims[_MAX_TIME_DIMS:]
    skipped += [d.column for d in extra_dims + extra_facts + extra_time]

    table_desc = (
        table_comment
        or f"{'Snapshot r' if snapshot else 'R'}ecords from {schema}.{table_name}."
    )

    return LogicalTable(
        logical_name=logical,
        physical_table=table_name,
        database=database,
        schema=schema,
        table_type=table_type,
        description=table_desc,
        dimensions=dims[:_MAX_DIMS],
        time_dimensions=time_dims[:_MAX_TIME_DIMS],
        facts=facts[:_MAX_FACTS],
        metrics=[count_metric] + derived_metrics,
        filters=filters,
        skipped_columns=skipped,
        is_snapshot=snapshot,
        primary_time_dim=primary_time,
    )


def _group_by_table(records: list[ColumnRecord]) -> dict[tuple, list[ColumnRecord]]:
    grouped: dict[tuple, list[ColumnRecord]] = defaultdict(list)
    for r in records:
        grouped[(r.database, r.schema, r.table, r.table_type, r.table_comment)].append(r)
    return grouped


# ── Relationship inference ────────────────────────────────────────────────────

def _infer_relationships(tables: list[LogicalTable]) -> list[Relationship]:
    rels: list[Relationship] = []
    seen: set[tuple] = set()

    def add(rel: Relationship) -> None:
        key = (rel.left_table, rel.right_table, rel.left_column, rel.right_column)
        if key not in seen:
            seen.add(key)
            rels.append(rel)

    # Build index: column_name_upper → list of tables that have it as unique
    unique_index: dict[str, list[LogicalTable]] = defaultdict(list)
    for t in tables:
        for dc in t.dimensions:
            if dc.is_unique:
                unique_index[dc.column.upper()].append(t)

    # Pass 1: LEI role-playing pattern
    # Find tables with a column named exactly "LEI" that is unique
    lei_tables = [t for t in tables if any(
        dc.column.upper() == "LEI" and dc.is_unique for dc in t.dimensions
    )]
    if not lei_tables:
        # Fallback: any table with a dimension named "lei" (even if not marked unique)
        lei_tables = [t for t in tables if any(dc.name == "lei" for dc in t.dimensions)]

    for left in tables:
        for dc in left.dimensions:
            col_lower = dc.column.lower()
            if col_lower.endswith("_lei") and col_lower != "lei":
                role = col_lower[:-4]  # strip "_lei"
                for right in lei_tables:
                    if right.logical_name == left.logical_name:
                        continue
                    rel_name = f"{left.logical_name}_to_{_pluralize(role)}"
                    add(Relationship(
                        name=rel_name,
                        left_table=left.logical_name,
                        right_table=right.logical_name,
                        left_column=dc.column,
                        right_column="LEI",
                    ))

    # Pass 2: generic _id FK matching
    logical_name_index: dict[str, LogicalTable] = {t.logical_name: t for t in tables}

    for left in tables:
        for dc in left.dimensions:
            col_lower = dc.column.lower()
            if not col_lower.endswith("_id"):
                continue
            prefix = col_lower[:-3]  # strip "_id"
            # Try singular then plural
            candidates = [
                logical_name_index.get(prefix),
                logical_name_index.get(_pluralize(prefix)),
            ]
            for right in candidates:
                if right is None or right.logical_name == left.logical_name:
                    continue
                # Confirm right table has a matching column
                right_col = next(
                    (d for d in right.dimensions if d.column.lower() == col_lower),
                    None,
                )
                if right_col is None:
                    # Accept if right table has any column ending in _id that is unique
                    right_col = next(
                        (d for d in right.dimensions if d.column.lower() == col_lower and d.is_unique),
                        None,
                    )
                if right_col is None:
                    # Loose match: right table has same column name (case-insensitive)
                    right_col = next(
                        (d for d in right.dimensions if d.column.upper() == dc.column.upper()),
                        None,
                    )
                if right_col is not None:
                    add(Relationship(
                        name=f"{left.logical_name}_to_{right.logical_name}",
                        left_table=left.logical_name,
                        right_table=right.logical_name,
                        left_column=dc.column,
                        right_column=right_col.column,
                    ))
                break

    return rels


# ── View-level derived metrics ────────────────────────────────────────────────

def _derive_view_metrics(tables: list[LogicalTable]) -> list[MetricSpec]:
    """Generate cross-table ratio metrics when two tables share USD-suffixed metrics."""
    usd_metrics: list[tuple[str, str]] = []  # (table_logical, metric_name)
    for t in tables:
        for m in t.metrics:
            if m.name.endswith("_usd") or "_usd_" in m.name:
                usd_metrics.append((t.logical_name, m.name))

    if len(usd_metrics) < 2:
        return []

    # Emit one ratio between the first two USD metrics from different tables
    (ta, ma), (tb, mb) = usd_metrics[0], usd_metrics[1]
    if ta == tb:
        return []

    return [MetricSpec(
        name=f"{ma}_to_{mb}_ratio",
        description=(
            f"Ratio of {ma.replace('_', ' ')} to {mb.replace('_', ' ')}. "
            "Use only when time bases are aligned. Example question: "
            f"'What is the ratio of {ma.replace('_', ' ')} to {mb.replace('_', ' ')}?'"
        ),
        expr=f"{ta}.{ma} / NULLIF({tb}.{mb}, 0)",
        access_modifier="public_access",
    )]


# ── Verified queries ──────────────────────────────────────────────────────────

def _build_verified_queries(
    tables: list[LogicalTable], view_name: str
) -> list[dict]:
    if not tables:
        return []

    primary = tables[0]
    queries = []

    # 1. Top-N by first metric and first dimension
    if primary.dimensions and primary.metrics:
        dim = primary.dimensions[0]
        met = next((m for m in primary.metrics if m.name != f"{primary.logical_name}_count"), None)
        if met is None:
            met = primary.metrics[0]
        queries.append({
            "name": f"top_{dim.name}_by_{met.name}",
            "question": f"What are the top 10 {dim.name.replace('_', ' ')} by {met.name.replace('_', ' ')}?",
            "sql": (
                f"SELECT\n"
                f"  {primary.logical_name}.{dim.name},\n"
                f"  {primary.logical_name}.{met.name}\n"
                f"FROM {view_name}\n"
                f"GROUP BY {primary.logical_name}.{dim.name}\n"
                f"ORDER BY {primary.logical_name}.{met.name} DESC\n"
                f"LIMIT 10"
            ),
            "use_as_onboarding_question": True,
        })

    # 2. Metric over time
    time_table = next((t for t in tables if t.time_dimensions and t.metrics), None)
    if time_table:
        td = time_table.time_dimensions[0]
        met = next(
            (m for m in time_table.metrics if m.name != f"{time_table.logical_name}_count"),
            time_table.metrics[0],
        )
        queries.append({
            "name": f"{met.name}_by_{td.name}",
            "question": f"What is {met.name.replace('_', ' ')} by {td.name.replace('_', ' ')}?",
            "sql": (
                f"SELECT\n"
                f"  {time_table.logical_name}.{td.name},\n"
                f"  {time_table.logical_name}.{met.name}\n"
                f"FROM {view_name}\n"
                f"GROUP BY {time_table.logical_name}.{td.name}\n"
                f"ORDER BY {time_table.logical_name}.{td.name} DESC"
            ),
        })

    # 3. Snapshot metric at latest date, or generic second-dimension aggregate
    snap_table = next((t for t in tables if t.is_snapshot and t.time_dimensions and t.metrics), None)
    if snap_table:
        td = snap_table.time_dimensions[0]
        met = next(
            (m for m in snap_table.metrics if m.non_additive_dimensions),
            snap_table.metrics[0],
        )
        dim2 = snap_table.dimensions[0] if snap_table.dimensions else None
        if dim2:
            queries.append({
                "name": f"{met.name}_at_latest_{td.name}",
                "question": (
                    f"What is {met.name.replace('_', ' ')} by "
                    f"{dim2.name.replace('_', ' ')} at the latest {td.name.replace('_', ' ')}?"
                ),
                "sql": (
                    f"SELECT\n"
                    f"  {snap_table.logical_name}.{dim2.name},\n"
                    f"  {snap_table.logical_name}.{met.name}\n"
                    f"FROM {view_name}\n"
                    f"WHERE {snap_table.logical_name}.{td.name} = "
                    f"(SELECT MAX({snap_table.logical_name}.{td.name}) FROM {view_name})\n"
                    f"GROUP BY {snap_table.logical_name}.{dim2.name}\n"
                    f"ORDER BY {snap_table.logical_name}.{met.name} DESC\n"
                    f"LIMIT 10"
                ),
            })
    elif len(tables) > 1 and tables[1].dimensions and tables[1].metrics:
        t2 = tables[1]
        dim2 = t2.dimensions[0]
        met2 = next(
            (m for m in t2.metrics if m.name != f"{t2.logical_name}_count"),
            t2.metrics[0],
        )
        queries.append({
            "name": f"{met2.name}_by_{dim2.name}",
            "question": f"What is {met2.name.replace('_', ' ')} by {dim2.name.replace('_', ' ')}?",
            "sql": (
                f"SELECT\n"
                f"  {t2.logical_name}.{dim2.name},\n"
                f"  {t2.logical_name}.{met2.name}\n"
                f"FROM {view_name}\n"
                f"GROUP BY {t2.logical_name}.{dim2.name}\n"
                f"ORDER BY {t2.logical_name}.{met2.name} DESC\n"
                f"LIMIT 10"
            ),
        })

    return queries[:3]


# ── YAML rendering ────────────────────────────────────────────────────────────

def _field_dict(dc: DescribedColumn) -> dict:
    d: dict = {}
    d["name"] = dc.name
    if dc.synonyms:
        d["synonyms"] = dc.synonyms
    d["description"] = dc.description
    d["expr"] = dc.expr
    d["data_type"] = dc.data_type
    if dc.is_unique:
        d["unique"] = True
    return d


def _metric_dict(m: MetricSpec) -> dict:
    d: dict = {}
    d["name"] = m.name
    if m.synonyms:
        d["synonyms"] = m.synonyms
    d["description"] = m.description
    d["expr"] = m.expr
    if m.non_additive_dimensions:
        d["non_additive_dimensions"] = m.non_additive_dimensions
    if m.access_modifier != "public_access":
        d["access_modifier"] = m.access_modifier
    return d


def _render_yaml(
    view_name: str,
    description: str,
    tables: list[LogicalTable],
    relationships: list[Relationship],
    view_metrics: list[MetricSpec],
    verified_queries: list[dict],
) -> str:
    doc: dict = {}
    doc["name"] = view_name
    doc["description"] = description

    doc_tables = []
    for t in tables:
        td: dict = {}
        td["name"] = t.logical_name
        if t.skipped_columns:
            td["_skipped_columns_manual_review"] = t.skipped_columns
        td["description"] = t.description
        td["base_table"] = {
            "database": t.database,
            "schema": t.schema,
            "table": t.physical_table,
        }
        if t.dimensions:
            td["dimensions"] = [_field_dict(d) for d in t.dimensions]
        if t.time_dimensions:
            td["time_dimensions"] = [_field_dict(d) for d in t.time_dimensions]
        if t.facts:
            td["facts"] = [_field_dict(d) for d in t.facts]
        if t.metrics:
            td["metrics"] = [_metric_dict(m) for m in t.metrics]
        if t.filters:
            td["filters"] = t.filters
        doc_tables.append(td)
    doc["tables"] = doc_tables

    if relationships:
        doc["relationships"] = [
            {
                "name": r.name,
                "left_table": r.left_table,
                "right_table": r.right_table,
                "relationship_columns": [
                    {"left_column": r.left_column, "right_column": r.right_column}
                ],
            }
            for r in relationships
        ]

    if view_metrics:
        doc["metrics"] = [_metric_dict(m) for m in view_metrics]

    if verified_queries:
        doc["verified_queries"] = verified_queries

    return yaml.dump(doc, default_flow_style=False, allow_unicode=True, sort_keys=False)


# ── SQL rendering ─────────────────────────────────────────────────────────────

def _snapshot_metric_names(tables: list[LogicalTable]) -> list[str]:
    names = []
    for t in tables:
        for m in t.metrics:
            if m.non_additive_dimensions:
                names.append(f"{t.logical_name}.{m.name}")
    return names


def _render_sql(
    view_name: str,
    database: str,
    schema: str,
    yaml_content: str,
    tables: list[LogicalTable],
    primary_time_dim: str | None,
) -> str:
    fq_schema = f"{database}.{schema}"
    fq_view = f"{database}.{schema}.{view_name}"
    snapshot_metrics = _snapshot_metric_names(tables)
    snap_list = ", ".join(snapshot_metrics) if snapshot_metrics else "(none)"
    domain = schema.lower().replace("_", " ")
    time_default = primary_time_dim.replace("_", " ") if primary_time_dim else "the most recent date"

    sql_gen_instructions = (
        f"Business context: This semantic view covers {domain} data.\\n"
        f"Default date basis: use {time_default} unless the user specifies otherwise.\\n"
        f"Prefer semantic metrics over recomputing raw column expressions.\\n"
        f"Snapshot metrics ({snap_list}) require a single date filter; "
        f"do not aggregate them across dates unless the user asks for a time series."
    )

    q_cat_instructions = (
        "Clarify date basis when a user asks for current or latest values without specifying a date.\\n"
        "Reject questions about data not represented in this semantic view.\\n"
        "Do not fabricate joins, metrics, or definitions that are not in the model."
    )

    # Escape $$ in yaml for use inside $$…$$ dollar quoting
    yaml_escaped = yaml_content.replace("$$", "\\$\\$")

    lines = [
        "-- ============================================================",
        f"-- Semantic view: {fq_view}",
        f"-- Generated by tools/semantic_brainstormer.py",
        "-- ============================================================",
        "",
        "-- Step 1: Validate (verify_only = TRUE — no changes made)",
        "SELECT SYSTEM$CREATE_SEMANTIC_VIEW_FROM_YAML(",
        f"  '{fq_schema}',",
        "  $$",
        yaml_escaped.rstrip(),
        "  $$,",
        "  TRUE",
        ");",
        "",
        "-- Step 2: Create the semantic view (remove the TRUE flag to execute)",
        "-- Uncomment the block below after Step 1 passes.",
        "/*",
        "SELECT SYSTEM$CREATE_SEMANTIC_VIEW_FROM_YAML(",
        f"  '{fq_schema}',",
        "  $$",
        yaml_escaped.rstrip(),
        "  $$,",
        "  FALSE",
        ");",
        "",
        "-- Step 3: Apply Cortex Analyst instructions",
        f"ALTER SEMANTIC VIEW {fq_view}",
        f"  SET AI_SQL_GENERATION = '{sql_gen_instructions}';",
        "",
        f"ALTER SEMANTIC VIEW {fq_view}",
        f"  SET AI_QUESTION_CATEGORIZATION = '{q_cat_instructions}';",
        "*/",
    ]
    return "\n".join(lines) + "\n"


# ── Output helpers ────────────────────────────────────────────────────────────

def _ensure_gitignore(repo_root: Path) -> None:
    gitignore = repo_root / ".gitignore"
    content = gitignore.read_text() if gitignore.exists() else ""
    if "generated/" not in content:
        gitignore.write_text(content.rstrip() + "\ngenerated/\n")


def _write_outputs(
    output_dir: Path,
    view_name: str,
    yaml_content: str,
    sql_content: str,
) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    yaml_path = output_dir / f"{view_name}.yaml"
    sql_path = output_dir / f"{view_name}_create.sql"
    yaml_path.write_text(yaml_content, encoding="utf-8")
    sql_path.write_text(sql_content, encoding="utf-8")
    return yaml_path, sql_path


# ── CLI ───────────────────────────────────────────────────────────────────────

def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Generate Snowflake Semantic View YAML and SQL from live schema introspection.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--database", required=True, help="Snowflake database to introspect.")
    p.add_argument(
        "--schemas", required=True,
        help="Comma-separated schema names, e.g. MART_FINANCE,MART_RISK",
    )
    p.add_argument(
        "--connection", default=None,
        help="Snow CLI connection profile name from ~/.snowflake/config.toml. "
             "Omit to use the default profile.",
    )
    p.add_argument(
        "--view-name", default=None,
        help="Name for the generated semantic view. "
             "Defaults to <database>_semantic_view (lowercase).",
    )
    p.add_argument(
        "--output-dir", default="generated/",
        help="Directory to write output files. Default: generated/",
    )
    p.add_argument(
        "--tables-filter", default=None,
        help="Comma-separated substrings; only include tables whose names contain at least one.",
    )
    p.add_argument(
        "--create", action="store_true",
        help="Execute the SQL against Snowflake to create the semantic view.",
    )
    p.add_argument("--verbose", action="store_true", help="Print classification details.")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    database: str = args.database.upper()
    schemas: list[str] = [s.strip().upper() for s in args.schemas.split(",") if s.strip()]
    view_name: str = (
        args.view_name
        or f"{database.lower()}_semantic_view"
    )
    output_dir = Path(args.output_dir)

    # ── Connect ───────────────────────────────────────────────────────────────
    print(f"Connecting to Snowflake (database={database}, connection={args.connection or 'default'}) …",
          file=sys.stderr)
    try:
        conn = get_connection(connection_name=args.connection, database=database)
    except (FileNotFoundError, KeyError) as exc:
        print(f"[error] {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"[error] Connection failed: {exc}", file=sys.stderr)
        return 1

    # ── Introspect ────────────────────────────────────────────────────────────
    print(f"Introspecting schemas: {schemas} …", file=sys.stderr)
    try:
        records = introspect_schemas(conn, database, schemas)
    except Exception as exc:
        print(f"[error] Schema introspection failed: {exc}", file=sys.stderr)
        print(
            "Hint: ensure your role has USAGE on the schema and can query INFORMATION_SCHEMA.",
            file=sys.stderr,
        )
        return 1

    if not records:
        print(f"[error] No tables found in {database}.{schemas}.", file=sys.stderr)
        return 2

    # ── Optional table filter ─────────────────────────────────────────────────
    filters_list = (
        [f.strip() for f in args.tables_filter.split(",") if f.strip()]
        if args.tables_filter else []
    )
    if filters_list:
        records = [
            r for r in records
            if any(f.upper() in r.table.upper() for f in filters_list)
        ]
        if not records:
            print(f"[error] No tables matched --tables-filter '{args.tables_filter}'.", file=sys.stderr)
            return 2

    # ── Build logical tables ──────────────────────────────────────────────────
    from collections import defaultdict
    grouped: dict[tuple, list[ColumnRecord]] = defaultdict(list)
    for r in records:
        grouped[(r.database, r.schema, r.table, r.table_type, r.table_comment)].append(r)

    # Handle logical name collisions across schemas
    logical_name_counts: dict[str, int] = defaultdict(int)
    for (db, sch, tbl, _, _) in grouped:
        logical_name_counts[_derive_logical_name(tbl)] += 1

    tables: list[LogicalTable] = []
    for (db, sch, tbl, tbl_type, tbl_comment), cols in grouped.items():
        if args.verbose:
            print(f"  Processing {sch}.{tbl} ({len(cols)} columns) …", file=sys.stderr)
        lt = _build_logical_table(tbl, sch, db, tbl_type, tbl_comment, cols, args.verbose)
        if lt is None:
            continue
        # Disambiguate logical names when the same name appears across multiple schemas
        if logical_name_counts[lt.logical_name] > 1:
            lt.logical_name = f"{sch.lower()}_{lt.logical_name}"
        tables.append(lt)

    if not tables:
        print("[error] No tables could be classified — all were skipped.", file=sys.stderr)
        return 2

    # ── Infer relationships ───────────────────────────────────────────────────
    relationships = _infer_relationships(tables)
    if args.verbose:
        for r in relationships:
            print(f"  [rel] {r.name}: {r.left_table}.{r.left_column} → "
                  f"{r.right_table}.{r.right_column}", file=sys.stderr)

    # ── View-level metrics ────────────────────────────────────────────────────
    view_metrics = _derive_view_metrics(tables)

    # ── Verified queries ──────────────────────────────────────────────────────
    verified_queries = _build_verified_queries(tables, view_name)

    # ── Description ───────────────────────────────────────────────────────────
    schema_desc = " and ".join(schemas)
    description = (
        f"Semantic view over {schema_desc} in {database}. "
        f"Covers {len(tables)} logical table(s): "
        f"{', '.join(t.logical_name for t in tables)}."
    )

    # ── Render YAML ───────────────────────────────────────────────────────────
    yaml_content = _render_yaml(
        view_name, description, tables, relationships, view_metrics, verified_queries
    )

    # ── Render SQL ────────────────────────────────────────────────────────────
    primary_time = next(
        (t.primary_time_dim for t in tables if t.primary_time_dim), None
    )
    primary_schema = schemas[0]
    sql_content = _render_sql(
        view_name, database, primary_schema, yaml_content, tables, primary_time
    )

    # ── Write files ───────────────────────────────────────────────────────────
    repo_root = Path(__file__).parent.parent
    _ensure_gitignore(repo_root)

    try:
        yaml_path, sql_path = _write_outputs(output_dir, view_name, yaml_content, sql_content)
    except OSError as exc:
        print(f"[error] Could not write output files: {exc}", file=sys.stderr)
        return 3

    print(f"YAML written → {yaml_path}", file=sys.stderr)
    print(f"SQL  written → {sql_path}", file=sys.stderr)

    # ── Optionally execute SQL to create the view ─────────────────────────────
    if args.create:
        print("Validating semantic view in Snowflake …", file=sys.stderr)
        try:
            cursor = conn.get_cursor()
            cursor.execute(
                f"SELECT SYSTEM$CREATE_SEMANTIC_VIEW_FROM_YAML("
                f"  '{database}.{primary_schema}', $${yaml_content}$$, TRUE)"
            )
            result = cursor.fetchone()
            print(f"  Validation result: {result[0] if result else 'OK'}", file=sys.stderr)

            print("Creating semantic view …", file=sys.stderr)
            cursor.execute(
                f"SELECT SYSTEM$CREATE_SEMANTIC_VIEW_FROM_YAML("
                f"  '{database}.{primary_schema}', $${yaml_content}$$, FALSE)"
            )
            print(f"  Created: {database}.{primary_schema}.{view_name}", file=sys.stderr)

            sql_gen = (
                f"Business context: covers {schema_desc} data. "
                f"Default date basis: {primary_time or 'most recent date'}. "
                "Prefer semantic metrics. Snapshot metrics require a single date filter."
            )
            q_cat = (
                "Clarify date basis when user asks for current values without a date. "
                "Reject questions about data not in this view."
            )
            cursor.execute(
                f"ALTER SEMANTIC VIEW {database}.{primary_schema}.{view_name} "
                f"SET AI_SQL_GENERATION = '{sql_gen}'"
            )
            cursor.execute(
                f"ALTER SEMANTIC VIEW {database}.{primary_schema}.{view_name} "
                f"SET AI_QUESTION_CATEGORIZATION = '{q_cat}'"
            )
            print(f"  Cortex Analyst instructions applied.", file=sys.stderr)
            print(f"{database}.{primary_schema}.{view_name}")
        except Exception as exc:
            print(f"[error] Snowflake execution failed: {exc}", file=sys.stderr)
            print("Files were written. Review the SQL and run it manually.", file=sys.stderr)
            return 3

    return 0


if __name__ == "__main__":
    sys.exit(main())
