"""
Convert Power BI PBIX semantic models to Snowflake Semantic View artifacts.

The converter uses pbixray to inspect a .pbix or PowerPivot .xlsx file and
generates:

  - <view_name>.yaml
  - <view_name>_create.sql
  - <view_name>_conversion_notes.md

Usage:
  python3 -m tools.pbixray_semantic_converter \\
    --pbix ./reports/sales.pbix \\
    --snowflake-database ANALYTICS \\
    --snowflake-schema MART_SALES \\
    --view-name sales_semantic_view \\
    --output-dir generated/pbix_sales \\
    --root-table Sales \\
    --table-map Sales=FACT_SALES,Date=DIM_DATE
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from tools.column_describer import (
    DescribedColumn,
    MetricSpec,
    derive_metrics,
    describe_column,
    is_snapshot_table,
)
from tools.relationship_inferencer import (
    ExplicitRelationship,
    InferenceColumn,
    InferenceTable,
    infer_relationships,
)
from tools.schema_introspector import ColumnRecord


@dataclass
class PbiColumn:
    table: str
    column: str
    pandas_type: str = ""
    dax_type: str = ""
    is_hidden: bool = False
    description: str | None = None


@dataclass
class PbiRelationship:
    from_table: str
    from_column: str
    to_table: str
    to_column: str
    is_active: bool = True
    cardinality: str = ""
    cross_filtering_behavior: str = ""
    from_key_count: int | None = None
    to_key_count: int | None = None
    rely_on_referential_integrity: bool | None = None


@dataclass
class PbiMeasure:
    table: str
    name: str
    expression: str
    display_folder: str = ""
    description: str = ""


@dataclass
class LogicalTable:
    logical_name: str
    powerbi_table: str
    physical_table: str
    database: str
    schema: str
    description: str
    dimensions: list[dict] = field(default_factory=list)
    time_dimensions: list[dict] = field(default_factory=list)
    facts: list[dict] = field(default_factory=list)
    metrics: list[dict] = field(default_factory=list)
    filters: list[dict] = field(default_factory=list)
    skipped_columns: list[str] = field(default_factory=list)
    is_root: bool = False
    is_snapshot: bool = False
    primary_time_dim: str | None = None


@dataclass
class SemanticRelationship:
    name: str
    left_table: str
    right_table: str
    left_column: str
    right_column: str
    source: PbiRelationship | None = None


@dataclass
class ConversionResult:
    yaml_content: str
    sql_content: str
    notes_content: str
    root_table: str
    yaml_path: Path | None = None
    sql_path: Path | None = None
    notes_path: Path | None = None


_AGG_DAX_RE = re.compile(
    r"^\s*(?P<fn>SUM|AVERAGE|MIN|MAX|COUNT|DISTINCTCOUNT)\s*\(\s*"
    r"(?:(?:'(?P<table_q>[^']+)')|(?P<table>[A-Za-z0-9_ .-]+))?"
    r"\[(?P<column>[^\]]+)\]\s*\)\s*$",
    re.IGNORECASE,
)
_COUNTROWS_DAX_RE = re.compile(
    r"^\s*COUNTROWS\s*\(\s*(?:'(?P<table_q>[^']+)'|(?P<table>[A-Za-z0-9_ .-]+))\s*\)\s*$",
    re.IGNORECASE,
)
_DIVIDE_MEASURES_RE = re.compile(
    r"^\s*DIVIDE\s*\(\s*\[(?P<num>[^\]]+)\]\s*,\s*\[(?P<den>[^\]]+)\]"
    r"(?:\s*,\s*(?P<alt>[^\)]+))?\s*\)\s*$",
    re.IGNORECASE,
)

_TIME_HINTS = ("date", "time", "timestamp", "datetime", "created", "updated")
_ROOT_NAME_HINTS = (
    "fact",
    "sales",
    "order",
    "orders",
    "transaction",
    "transactions",
    "event",
    "events",
    "line",
    "snapshot",
    "balance",
    "position",
    "holding",
    "exposure",
)
_DIM_NAME_HINTS = ("dim", "date", "customer", "product", "account", "entity", "party")


def _rows(frame: Any) -> list[dict[str, Any]]:
    """Return dict rows from a pandas dataframe, list of dicts, or missing value."""
    if frame is None:
        return []
    if hasattr(frame, "to_dict"):
        try:
            return [
                {str(k): _clean_scalar(v) for k, v in row.items()}
                for row in frame.to_dict("records")
            ]
        except TypeError:
            pass
    if isinstance(frame, list):
        result = []
        for row in frame:
            if isinstance(row, dict):
                result.append({str(k): _clean_scalar(v) for k, v in row.items()})
        return result
    return []


def _clean_scalar(value: Any) -> Any:
    try:
        if value != value:
            return None
    except Exception:
        pass
    return value


def _truthy(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() not in {"", "0", "false", "none", "nan", "inactive"}


def _as_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _snake(name: str) -> str:
    spaced = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name.strip())
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", spaced)
    clean = re.sub(r"[^0-9A-Za-z]+", "_", spaced)
    clean = re.sub(r"_+", "_", clean).strip("_").lower()
    if not clean:
        return "unnamed"
    if clean[0].isdigit():
        return f"_{clean}"
    return clean


def _physical_name(name: str) -> str:
    return _snake(name).upper()


def _snowflake_type(pandas_type: str, dax_type: str = "", column_name: str = "") -> str:
    text = f"{pandas_type} {dax_type}".lower()
    col = column_name.lower()
    if any(token in text for token in ("int", "decimal", "double", "float", "number", "currency")) and (
        col.endswith("key") or col.endswith("id") or col.endswith("_key") or col.endswith("_id")
    ):
        return "NUMBER"
    if any(hint in col for hint in _TIME_HINTS) or "datetime" in text or "date" in text:
        return "TIMESTAMP_NTZ" if "time" in text or "timestamp" in col else "DATE"
    if any(token in text for token in ("int", "decimal", "double", "float", "number", "currency")):
        return "NUMBER"
    if "bool" in text:
        return "BOOLEAN"
    return "VARCHAR"


def _table_rows_from_pbixray(model: Any) -> list[str]:
    tables = getattr(model, "tables", None)
    if tables is None:
        return []
    if hasattr(tables, "tolist"):
        return [str(t) for t in tables.tolist()]
    if isinstance(tables, list):
        return [str(t) for t in tables]
    return []


def extract_model_from_pbixray(model: Any) -> tuple[list[str], list[PbiColumn], list[PbiRelationship], list[PbiMeasure], dict[str, list[dict[str, Any]]]]:
    """Normalize the public pbixray properties into stable Python dataclasses."""
    tables = _table_rows_from_pbixray(model)

    tmschema_columns = _rows(getattr(model, "tmschema_columns", None))
    tmschema_by_key: dict[tuple[str, str], dict[str, Any]] = {}
    for row in tmschema_columns:
        table = row.get("TableName") or row.get("Table") or row.get("TableID")
        column = row.get("Name") or row.get("ColumnName")
        if table and column:
            tmschema_by_key[(str(table), str(column))] = row

    columns: list[PbiColumn] = []
    for row in _rows(getattr(model, "schema", None)):
        table = row.get("TableName")
        column = row.get("ColumnName") or row.get("Name")
        if not table or not column:
            continue
        tms = tmschema_by_key.get((str(table), str(column)), {})
        columns.append(
            PbiColumn(
                table=str(table),
                column=str(column),
                pandas_type=str(row.get("PandasDataType") or row.get("DataType") or ""),
                dax_type=str(tms.get("DataType") or ""),
                is_hidden=_truthy(tms.get("IsHidden"), default=False),
                description=(
                    str(tms.get("Description"))
                    if tms.get("Description") not in (None, "")
                    else None
                ),
            )
        )

    for col in columns:
        if col.table not in tables:
            tables.append(col.table)

    relationships: list[PbiRelationship] = []
    for row in _rows(getattr(model, "relationships", None)):
        from_table = row.get("FromTableName")
        from_column = row.get("FromColumnName")
        to_table = row.get("ToTableName")
        to_column = row.get("ToColumnName")
        if not all([from_table, from_column, to_table, to_column]):
            continue
        relationships.append(
            PbiRelationship(
                from_table=str(from_table),
                from_column=str(from_column),
                to_table=str(to_table),
                to_column=str(to_column),
                is_active=_truthy(row.get("IsActive"), default=True),
                cardinality=str(row.get("Cardinality") or ""),
                cross_filtering_behavior=str(row.get("CrossFilteringBehavior") or ""),
                from_key_count=_as_int(row.get("FromKeyCount")),
                to_key_count=_as_int(row.get("ToKeyCount")),
                rely_on_referential_integrity=(
                    _truthy(row.get("RelyOnReferentialIntegrity"), default=False)
                    if row.get("RelyOnReferentialIntegrity") is not None
                    else None
                ),
            )
        )

    measures: list[PbiMeasure] = []
    for row in _rows(getattr(model, "dax_measures", None)):
        table = row.get("TableName")
        name = row.get("Name")
        expression = row.get("Expression")
        if not all([table, name, expression]):
            continue
        measures.append(
            PbiMeasure(
                table=str(table),
                name=str(name),
                expression=str(expression),
                display_folder=str(row.get("DisplayFolder") or ""),
                description=str(row.get("Description") or ""),
            )
        )
        if str(table) not in tables:
            tables.append(str(table))

    extras = {
        "rls": _rows(getattr(model, "rls", None)),
        "dax_tables": _rows(getattr(model, "dax_tables", None)),
        "dax_columns": _rows(getattr(model, "dax_columns", None)),
        "power_query": _rows(getattr(model, "power_query", None)),
        "m_parameters": _rows(getattr(model, "m_parameters", None)),
    }
    return tables, columns, relationships, measures, extras


def _parse_table_map(raw: str | None) -> dict[str, str]:
    if not raw:
        return {}
    result: dict[str, str] = {}
    for part in raw.split(","):
        if not part.strip():
            continue
        if "=" not in part:
            raise ValueError("--table-map entries must use PowerBI=SNOWFLAKE_TABLE")
        left, right = part.split("=", 1)
        result[left.strip()] = right.strip().upper()
    return result


def _relationship_orientation(rel: PbiRelationship) -> tuple[str, str, str, str] | None:
    """Return left_table, left_column, right_table, right_column for Snowflake YAML."""
    card = re.sub(r"[^a-z]", "", rel.cardinality.lower())
    if "manytomany" in card:
        return None
    if "manytoone" in card:
        return rel.from_table, rel.from_column, rel.to_table, rel.to_column
    if "onetomany" in card:
        return rel.to_table, rel.to_column, rel.from_table, rel.from_column
    if "onetoone" in card:
        return rel.from_table, rel.from_column, rel.to_table, rel.to_column

    if rel.from_key_count is not None and rel.to_key_count is not None:
        if rel.from_key_count >= rel.to_key_count:
            return rel.from_table, rel.from_column, rel.to_table, rel.to_column
        return rel.to_table, rel.to_column, rel.from_table, rel.from_column

    return rel.from_table, rel.from_column, rel.to_table, rel.to_column


def _is_relationship_one_side(rel: PbiRelationship, table: str, column: str) -> bool:
    oriented = _relationship_orientation(rel)
    if oriented is None:
        return False
    _, _, right_table, right_column = oriented
    return table == right_table and column == right_column


def _is_relationship_key(relations: list[PbiRelationship], table: str, column: str) -> bool:
    for rel in relations:
        if table in {rel.from_table, rel.to_table} and column in {rel.from_column, rel.to_column}:
            return True
    return False


def _field_dict(dc: DescribedColumn, hidden: bool = False) -> dict[str, Any]:
    item: dict[str, Any] = {
        "name": dc.name,
        "description": dc.description,
        "expr": dc.expr,
        "data_type": dc.data_type,
    }
    if dc.synonyms:
        item["synonyms"] = dc.synonyms
    if dc.is_unique:
        item["unique"] = True
    if hidden:
        item["access_modifier"] = "private_access"
    return item


def _metric_dict(metric: MetricSpec) -> dict[str, Any]:
    item: dict[str, Any] = {
        "name": metric.name,
        "description": metric.description,
        "expr": metric.expr,
    }
    if metric.synonyms:
        item["synonyms"] = metric.synonyms
    if metric.non_additive_dimensions:
        item["non_additive_dimensions"] = metric.non_additive_dimensions
    if metric.access_modifier != "public_access":
        item["access_modifier"] = metric.access_modifier
    return item


def _primary_time_dim(fields: list[dict[str, Any]]) -> str | None:
    preferred = (
        "as_of_date",
        "snapshot_date",
        "order_date",
        "transaction_date",
        "sales_date",
        "date",
        "created_date",
    )
    names = {f["name"] for f in fields}
    for name in preferred:
        if name in names:
            return name
    return fields[0]["name"] if fields else None


def _root_table_scores(
    tables: list[str],
    columns_by_table: dict[str, list[PbiColumn]],
    relationships: list[PbiRelationship],
    measures: list[PbiMeasure],
) -> dict[str, int]:
    scores = {table: 0 for table in tables}
    for table in tables:
        low = table.lower()
        if any(hint in low for hint in _ROOT_NAME_HINTS):
            scores[table] += 4
        if any(low.startswith(hint) or f" {hint}" in low for hint in _DIM_NAME_HINTS):
            scores[table] -= 2
        for col in columns_by_table.get(table, []):
            sf_type = _snowflake_type(col.pandas_type, col.dax_type, col.column)
            if sf_type == "NUMBER" and not col.column.lower().endswith(("_id", "_key")):
                scores[table] += 1
    for rel in relationships:
        if not rel.is_active:
            continue
        oriented = _relationship_orientation(rel)
        if oriented is None:
            continue
        left_table, _, right_table, _ = oriented
        scores[left_table] = scores.get(left_table, 0) + 4
        scores[right_table] = scores.get(right_table, 0) - 1
    for measure in measures:
        scores[measure.table] = scores.get(measure.table, 0) + 3
    return scores


def _select_root_table(
    tables: list[str],
    columns_by_table: dict[str, list[PbiColumn]],
    relationships: list[PbiRelationship],
    measures: list[PbiMeasure],
    requested_root: str | None,
) -> tuple[str, dict[str, int]]:
    if not tables:
        raise ValueError("Power BI model has no tables to convert.")
    scores = _root_table_scores(tables, columns_by_table, relationships, measures)
    if requested_root:
        for table in tables:
            if table.lower() == requested_root.lower():
                return table, scores
        raise ValueError(f"Requested root table '{requested_root}' was not found in the PBIX model.")
    physical_tables = [table for table in tables if columns_by_table.get(table)]
    candidates = physical_tables or tables
    return sorted(candidates, key=lambda table: (-scores.get(table, 0), table.lower()))[0], scores


def _sanitize_measure_name(name: str) -> str:
    metric = _snake(name)
    if not metric:
        metric = "measure"
    return metric


def _translate_direct_dax(
    measure: PbiMeasure,
    table_lookup: dict[str, str],
    field_lookup: dict[tuple[str, str], str],
) -> tuple[str, str] | None:
    expression = measure.expression.strip()
    agg_match = _AGG_DAX_RE.match(expression)
    if agg_match:
        fn = agg_match.group("fn").upper()
        source_table = agg_match.group("table_q") or agg_match.group("table") or measure.table
        source_table = source_table.strip()
        source_col = agg_match.group("column").strip()
        logical_table = table_lookup.get(source_table)
        logical_col = field_lookup.get((source_table, source_col))
        if not logical_table or not logical_col:
            return None
        sql_fn = {
            "SUM": "SUM",
            "AVERAGE": "AVG",
            "MIN": "MIN",
            "MAX": "MAX",
            "COUNT": "COUNT",
            "DISTINCTCOUNT": "COUNT_DISTINCT",
        }[fn]
        if sql_fn == "COUNT_DISTINCT":
            return source_table, f"COUNT(DISTINCT {logical_col})"
        return source_table, f"{sql_fn}({logical_col})"

    countrows_match = _COUNTROWS_DAX_RE.match(expression)
    if countrows_match:
        source_table = countrows_match.group("table_q") or countrows_match.group("table")
        source_table = source_table.strip()
        if source_table in table_lookup:
            return source_table, "COUNT(*)"

    return None


def _translate_derived_dax(
    measure: PbiMeasure,
    measure_lookup: dict[str, tuple[str, str]],
) -> tuple[str, set[str]] | None:
    expression = measure.expression.strip()
    match = _DIVIDE_MEASURES_RE.match(expression)
    if not match:
        return None
    num = _sanitize_measure_name(match.group("num"))
    den = _sanitize_measure_name(match.group("den"))
    if num not in measure_lookup or den not in measure_lookup:
        return None
    num_table, num_metric = measure_lookup[num]
    den_table, den_metric = measure_lookup[den]
    refs = {num_table, den_table}
    if num_table == den_table:
        return f"{num_metric} / NULLIF({den_metric}, 0)", refs
    return f"{num_table}.{num_metric} / NULLIF({den_table}.{den_metric}, 0)", refs


def _build_logical_tables(
    tables: list[str],
    columns_by_table: dict[str, list[PbiColumn]],
    relationships: list[PbiRelationship],
    measures: list[PbiMeasure],
    database: str,
    schema: str,
    root_table: str,
    table_map: dict[str, str],
    include_hidden: bool,
) -> tuple[list[LogicalTable], dict[str, str], dict[tuple[str, str], str], list[str]]:
    logical_names = {table: _snake(table) for table in tables}
    field_lookup: dict[tuple[str, str], str] = {}
    warnings: list[str] = []
    result: list[LogicalTable] = []

    measure_tables = {m.table for m in measures}
    for table in tables:
        cols = columns_by_table.get(table, [])
        if not cols and table in measure_tables:
            warnings.append(
                f"Power BI table '{table}' contains measures only; its supported measures are relocated to their source/root table."
            )
            continue

        logical = logical_names[table]
        time_dims: list[dict[str, Any]] = []
        dims: list[dict[str, Any]] = []
        facts: list[dict[str, Any]] = []
        skipped: list[str] = []
        fact_columns: list[DescribedColumn] = []
        snapshot = is_snapshot_table(table)

        for pbi_col in cols:
            is_key = _is_relationship_key(relationships, table, pbi_col.column)
            semantic_column = _snake(pbi_col.column)
            is_key_like = semantic_column == "lei" or semantic_column.endswith(("_id", "_key"))
            if pbi_col.is_hidden and not include_hidden and not (is_key or is_key_like):
                skipped.append(pbi_col.column)
                continue

            sf_type = _snowflake_type(pbi_col.pandas_type, pbi_col.dax_type, pbi_col.column)
            unique = any(
                _is_relationship_one_side(rel, table, pbi_col.column)
                for rel in relationships
                if rel.is_active
            )
            record = ColumnRecord(
                database=database,
                schema=schema,
                table=table,
                table_type="BASE TABLE",
                column=semantic_column,
                datatype=sf_type,
                ordinal=0,
                is_nullable=True,
                is_unique=unique,
                column_comment=pbi_col.description,
            )
            described = describe_column(record, logical)
            described.expr = pbi_col.column
            field_lookup[(table, pbi_col.column)] = described.name

            if described.classification == "dimension":
                dims.append(_field_dict(described, hidden=pbi_col.is_hidden))
            elif described.classification == "time_dimension":
                time_dims.append(_field_dict(described, hidden=pbi_col.is_hidden))
            elif described.classification == "fact":
                facts.append(_field_dict(described, hidden=pbi_col.is_hidden))
                fact_columns.append(described)
            else:
                skipped.append(pbi_col.column)

        primary_time = _primary_time_dim(time_dims)
        metric_specs = derive_metrics(fact_columns, primary_time, snapshot)
        count_metric = MetricSpec(
            name=f"{logical}_count",
            expr="COUNT(*)",
            description=(
                f"Count of {logical.replace('_', ' ')} records from the Power BI semantic model. "
                f"Example question: 'How many {logical.replace('_', ' ')} are there?'"
            ),
        )
        metrics = [_metric_dict(count_metric)] + [_metric_dict(m) for m in metric_specs]

        result.append(
            LogicalTable(
                logical_name=logical,
                powerbi_table=table,
                physical_table=table_map.get(table, _physical_name(table)),
                database=database,
                schema=schema,
                description=(
                    f"Power BI table '{table}' mapped to Snowflake table "
                    f"{database}.{schema}.{table_map.get(table, _physical_name(table))}."
                ),
                dimensions=dims,
                time_dimensions=time_dims,
                facts=facts,
                metrics=metrics,
                skipped_columns=skipped,
                is_root=(table == root_table),
                is_snapshot=snapshot,
                primary_time_dim=primary_time,
            )
        )

    result.sort(key=lambda t: (not t.is_root, t.logical_name))
    return result, logical_names, field_lookup, warnings


def _build_relationships(
    relationships: list[PbiRelationship],
    logical_tables: list[LogicalTable],
) -> tuple[list[SemanticRelationship], list[str]]:
    inference_tables = []
    for table in logical_tables:
        columns = []
        for field in table.dimensions + table.time_dimensions + table.facts:
            columns.append(
                InferenceColumn(
                    name=field["name"],
                    physical_name=field["expr"],
                    data_type=field.get("data_type", ""),
                    is_unique=bool(field.get("unique")),
                    is_hidden=field.get("access_modifier") == "private_access",
                )
            )
        inference_tables.append(
            InferenceTable(
                logical_name=table.logical_name,
                source_name=table.powerbi_table,
                physical_name=table.physical_table,
                columns=columns,
            )
        )

    explicit_relationships = [
        ExplicitRelationship(
            from_table=rel.from_table,
            from_column=rel.from_column,
            to_table=rel.to_table,
            to_column=rel.to_column,
            is_active=rel.is_active,
            cardinality=rel.cardinality,
            from_key_count=rel.from_key_count,
            to_key_count=rel.to_key_count,
            source="Power BI",
        )
        for rel in relationships
    ]
    inference = infer_relationships(inference_tables, explicit_relationships)
    result = [
        SemanticRelationship(
            name=rel.name,
            left_table=rel.left_table,
            right_table=rel.right_table,
            left_column=rel.left_column,
            right_column=rel.right_column,
            source=None,
        )
        for rel in inference.relationships
    ]
    warnings = inference.warnings[:]
    for rel in inference.relationships:
        if rel.source != "explicit":
            warnings.append(
                f"Inferred relationship {rel.left_table}.{rel.left_column} -> "
                f"{rel.right_table}.{rel.right_column} with confidence {rel.confidence}: {rel.reason}."
            )
    return result, warnings


def _attach_powerbi_measures(
    logical_tables: list[LogicalTable],
    logical_names: dict[str, str],
    field_lookup: dict[tuple[str, str], str],
    measures: list[PbiMeasure],
) -> tuple[list[dict[str, Any]], list[str]]:
    by_logical = {table.logical_name: table for table in logical_tables}
    direct_measure_lookup: dict[str, tuple[str, str]] = {}
    view_metrics: list[dict[str, Any]] = []
    warnings: list[str] = []

    for measure in measures:
        metric_name = _sanitize_measure_name(measure.name)
        translated = _translate_direct_dax(measure, logical_names, field_lookup)
        if translated is None:
            continue
        source_table, expr = translated
        logical_table = logical_names[source_table]
        if logical_table not in by_logical:
            warnings.append(
                f"Skipped measure '{measure.name}' because source table '{source_table}' was not modeled."
            )
            continue
        description = (
            measure.description.strip()
            or f"Power BI DAX measure '{measure.name}' translated from: {measure.expression.strip()}"
        )
        metric = {
            "name": metric_name,
            "description": description,
            "expr": expr,
        }
        by_logical[logical_table].metrics.append(metric)
        direct_measure_lookup[metric_name] = (logical_table, metric_name)
        if measure.table != source_table:
            warnings.append(
                f"Relocated measure '{measure.name}' from Power BI table '{measure.table}' "
                f"to source table '{source_table}'."
            )

    for measure in measures:
        metric_name = _sanitize_measure_name(measure.name)
        if metric_name in direct_measure_lookup:
            continue
        translated = _translate_derived_dax(measure, direct_measure_lookup)
        if translated is None:
            warnings.append(
                f"Skipped unsupported DAX measure '{measure.name}': {measure.expression.strip()}"
            )
            continue
        expr, refs = translated
        metric = {
            "name": metric_name,
            "description": (
                measure.description.strip()
                or f"Power BI DAX measure '{measure.name}' translated from: {measure.expression.strip()}"
            ),
            "expr": expr,
        }
        if len(refs) == 1:
            only_table = next(iter(refs))
            by_logical[only_table].metrics.append(metric)
            direct_measure_lookup[metric_name] = (only_table, metric_name)
        else:
            view_metrics.append(metric)
    return view_metrics, warnings


def _build_verified_queries(root: LogicalTable, view_name: str) -> list[dict[str, Any]]:
    queries: list[dict[str, Any]] = []
    metric = next(
        (m for m in root.metrics if not m["name"].endswith("_count")),
        root.metrics[0] if root.metrics else None,
    )
    dimension = root.dimensions[0] if root.dimensions else None
    time_dim = root.time_dimensions[0] if root.time_dimensions else None

    if metric and dimension:
        queries.append(
            {
                "name": f"top_{dimension['name']}_by_{metric['name']}",
                "question": (
                    f"What are the top 10 {dimension['name'].replace('_', ' ')} "
                    f"by {metric['name'].replace('_', ' ')}?"
                ),
                "sql": (
                    f"SELECT\n"
                    f"  {root.logical_name}.{dimension['name']},\n"
                    f"  {root.logical_name}.{metric['name']}\n"
                    f"FROM {view_name}\n"
                    f"GROUP BY {root.logical_name}.{dimension['name']}\n"
                    f"ORDER BY {root.logical_name}.{metric['name']} DESC\n"
                    f"LIMIT 10"
                ),
                "use_as_onboarding_question": True,
            }
        )

    if metric and time_dim:
        queries.append(
            {
                "name": f"{metric['name']}_by_{time_dim['name']}",
                "question": (
                    f"What is {metric['name'].replace('_', ' ')} by "
                    f"{time_dim['name'].replace('_', ' ')}?"
                ),
                "sql": (
                    f"SELECT\n"
                    f"  {root.logical_name}.{time_dim['name']},\n"
                    f"  {root.logical_name}.{metric['name']}\n"
                    f"FROM {view_name}\n"
                    f"GROUP BY {root.logical_name}.{time_dim['name']}\n"
                    f"ORDER BY {root.logical_name}.{time_dim['name']} DESC"
                ),
            }
        )

    return queries


def _render_yaml(
    view_name: str,
    description: str,
    tables: list[LogicalTable],
    relationships: list[SemanticRelationship],
    view_metrics: list[dict[str, Any]],
    verified_queries: list[dict[str, Any]],
) -> str:
    doc: dict[str, Any] = {"name": view_name, "description": description}
    doc_tables = []
    for table in tables:
        item: dict[str, Any] = {
            "name": table.logical_name,
            "description": table.description,
            "base_table": {
                "database": table.database,
                "schema": table.schema,
                "table": table.physical_table,
            },
        }
        if table.dimensions:
            item["dimensions"] = table.dimensions
        if table.time_dimensions:
            item["time_dimensions"] = table.time_dimensions
        if table.facts:
            item["facts"] = table.facts
        if table.metrics:
            item["metrics"] = table.metrics
        if table.filters:
            item["filters"] = table.filters
        doc_tables.append(item)
    doc["tables"] = doc_tables
    if relationships:
        doc["relationships"] = [
            {
                "name": rel.name,
                "left_table": rel.left_table,
                "right_table": rel.right_table,
                "relationship_columns": [
                    {
                        "left_column": rel.left_column,
                        "right_column": rel.right_column,
                    }
                ],
            }
            for rel in relationships
        ]
    if view_metrics:
        doc["metrics"] = view_metrics
    if verified_queries:
        doc["verified_queries"] = verified_queries
    return yaml.dump(doc, default_flow_style=False, allow_unicode=True, sort_keys=False)


def _render_sql(
    view_name: str,
    database: str,
    schema: str,
    yaml_content: str,
    root_table: str,
) -> str:
    fq_schema = f"{database}.{schema}"
    fq_view = f"{database}.{schema}.{view_name}"
    yaml_escaped = yaml_content.replace("$$", "\\$\\$")
    sql_generation = (
        "Business context: This semantic view was converted from a Power BI PBIX semantic model.\\n"
        f"Root table: {root_table}. Use this as the default fact table when the question is ambiguous.\\n"
        "Prefer translated semantic metrics over recomputing raw columns.\\n"
        "Do not translate unsupported DAX, calculated tables, RLS rules, or inactive relationships unless they are explicitly modeled."
    )
    question_categorization = (
        "Ask for clarification when the requested Power BI measure was not translated.\\n"
        "Reject questions that depend on Power BI RLS, calculated tables, or unsupported DAX unless matching Snowflake logic has been modeled.\\n"
        "Do not invent joins beyond the active Power BI relationships converted into this semantic view."
    )

    return "\n".join(
        [
            "-- ============================================================",
            f"-- Semantic view: {fq_view}",
            "-- Generated by tools/pbixray_semantic_converter.py",
            "-- ============================================================",
            "",
            "-- Step 1: Validate (verify_only = TRUE, no changes made)",
            "SELECT SYSTEM$CREATE_SEMANTIC_VIEW_FROM_YAML(",
            f"  '{fq_schema}',",
            "  $$",
            yaml_escaped.rstrip(),
            "  $$,",
            "  TRUE",
            ");",
            "",
            "-- Step 2: Create the semantic view only after validation passes.",
            "/*",
            "SELECT SYSTEM$CREATE_SEMANTIC_VIEW_FROM_YAML(",
            f"  '{fq_schema}',",
            "  $$",
            yaml_escaped.rstrip(),
            "  $$,",
            "  FALSE",
            ");",
            "",
            f"ALTER SEMANTIC VIEW {fq_view}",
            f"  SET AI_SQL_GENERATION = '{sql_generation}';",
            "",
            f"ALTER SEMANTIC VIEW {fq_view}",
            f"  SET AI_QUESTION_CATEGORIZATION = '{question_categorization}';",
            "*/",
            "",
        ]
    )


def _render_notes(
    root_table: str,
    root_scores: dict[str, int],
    warnings: list[str],
    extras: dict[str, list[dict[str, Any]]],
) -> str:
    lines = [
        "# PBIX to Snowflake Semantic View Conversion Notes",
        "",
        "## Decision Trace",
        "",
        f"- Root table selected: `{root_table}`.",
        "- Root selection uses active relationship direction, measure ownership, numeric fact-like columns, and table-name hints.",
        "- Direct aggregate DAX measures are translated to Snowflake metric expressions.",
        "- Unsupported DAX remains out of the YAML so validation does not create misleading metrics.",
        "- RLS, calculated tables, and calculated columns are documented as migration work, not silently embedded.",
        "",
        "## 5-Whys",
        "",
        "1. Why use pbixray? Because PBIX files are packaged Power BI artifacts and pbixray exposes model metadata without opening Power BI Desktop.",
        "2. Why find a root table? Because verified queries and ambiguous metric prompts need a stable fact-like starting point.",
        "3. Why use active relationships only? Because inactive relationships in Power BI require explicit DAX activation semantics that Snowflake relationships do not infer.",
        "4. Why translate only common DAX patterns? Because literal DAX-to-SQL translation is unsafe for filters, row context, calculation groups, and RLS.",
        "5. Why emit validation SQL first? Because Snowflake Semantic View YAML should be verified before any create/replace operation.",
        "",
        "## Root Table Scores",
        "",
    ]
    for table, score in sorted(root_scores.items(), key=lambda item: (-item[1], item[0].lower())):
        lines.append(f"- `{table}`: {score}")

    if warnings:
        lines.extend(["", "## Manual Review Items", ""])
        for warning in warnings:
            lines.append(f"- {warning}")

    if extras.get("rls"):
        lines.extend(["", "## Row-Level Security", ""])
        lines.append("- Power BI RLS was found. Translate it to Snowflake governance/RBAC or secure views before production use.")
    if extras.get("dax_tables"):
        lines.extend(["", "## DAX Calculated Tables", ""])
        for row in extras["dax_tables"]:
            lines.append(f"- `{row.get('TableName', 'unknown')}` requires manual Snowflake SQL modeling.")
    if extras.get("dax_columns"):
        lines.extend(["", "## DAX Calculated Columns", ""])
        for row in extras["dax_columns"]:
            lines.append(
                f"- `{row.get('TableName', 'unknown')}.{row.get('ColumnName', 'unknown')}` requires manual Snowflake SQL modeling."
            )
    if extras.get("power_query"):
        lines.extend(["", "## Power Query Sources", ""])
        lines.append("- Power Query expressions were extracted for reference, but source-table parsing is not trusted for physical Snowflake table mapping.")

    lines.extend(["", "## Deployment Rule", "", "- Run the generated verify-only SQL first. Create the semantic view only after manual review passes."])
    return "\n".join(lines) + "\n"


def convert_powerbi_model(
    *,
    tables: list[str],
    columns: list[PbiColumn],
    relationships: list[PbiRelationship],
    measures: list[PbiMeasure],
    extras: dict[str, list[dict[str, Any]]] | None,
    snowflake_database: str,
    snowflake_schema: str,
    view_name: str,
    root_table: str | None = None,
    table_map: dict[str, str] | None = None,
    include_hidden: bool = False,
) -> ConversionResult:
    extras = extras or {}
    table_map = table_map or {}
    database = snowflake_database.upper()
    schema = snowflake_schema.upper()

    columns_by_table: dict[str, list[PbiColumn]] = defaultdict(list)
    for col in columns:
        columns_by_table[col.table].append(col)
        if col.table not in tables:
            tables.append(col.table)
    for measure in measures:
        if measure.table not in tables:
            tables.append(measure.table)

    selected_root, scores = _select_root_table(
        tables, columns_by_table, relationships, measures, root_table
    )
    logical_tables, logical_names, field_lookup, table_warnings = _build_logical_tables(
        tables,
        columns_by_table,
        relationships,
        measures,
        database,
        schema,
        selected_root,
        table_map,
        include_hidden,
    )
    semantic_relationships, relationship_warnings = _build_relationships(
        relationships, logical_tables
    )
    view_metrics, measure_warnings = _attach_powerbi_measures(
        logical_tables, logical_names, field_lookup, measures
    )

    root_logical = next((t for t in logical_tables if t.powerbi_table == selected_root), None)
    if root_logical is None:
        raise ValueError(
            f"Selected root table '{selected_root}' has no physical columns. "
            "Choose a root table that maps to a Snowflake base table."
        )
    verified_queries = _build_verified_queries(root_logical, view_name)
    description = (
        f"Snowflake Semantic View converted from a Power BI PBIX semantic model. "
        f"Root table is '{selected_root}'. Review unsupported DAX, RLS, calculated tables, "
        f"and physical table mappings before production deployment."
    )
    yaml_content = _render_yaml(
        view_name,
        description,
        logical_tables,
        semantic_relationships,
        view_metrics,
        verified_queries,
    )
    sql_content = _render_sql(view_name, database, schema, yaml_content, selected_root)
    notes_content = _render_notes(
        selected_root,
        scores,
        table_warnings + relationship_warnings + measure_warnings,
        extras,
    )
    return ConversionResult(
        yaml_content=yaml_content,
        sql_content=sql_content,
        notes_content=notes_content,
        root_table=selected_root,
    )


def convert_pbix_file(
    pbix_path: Path,
    *,
    snowflake_database: str,
    snowflake_schema: str,
    view_name: str,
    root_table: str | None = None,
    table_map: dict[str, str] | None = None,
    include_hidden: bool = False,
) -> ConversionResult:
    try:
        from pbixray import PBIXRay
    except ImportError as exc:
        raise RuntimeError(
            "pbixray is required for PBIX conversion. Install project requirements or run: "
            "pip install pbixray"
        ) from exc

    model = PBIXRay(str(pbix_path))
    tables, columns, relationships, measures, extras = extract_model_from_pbixray(model)
    return convert_powerbi_model(
        tables=tables,
        columns=columns,
        relationships=relationships,
        measures=measures,
        extras=extras,
        snowflake_database=snowflake_database,
        snowflake_schema=snowflake_schema,
        view_name=view_name,
        root_table=root_table,
        table_map=table_map,
        include_hidden=include_hidden,
    )


def write_conversion(result: ConversionResult, output_dir: Path, view_name: str) -> ConversionResult:
    output_dir.mkdir(parents=True, exist_ok=True)
    result.yaml_path = output_dir / f"{view_name}.yaml"
    result.sql_path = output_dir / f"{view_name}_create.sql"
    result.notes_path = output_dir / f"{view_name}_conversion_notes.md"
    result.yaml_path.write_text(result.yaml_content, encoding="utf-8")
    result.sql_path.write_text(result.sql_content, encoding="utf-8")
    result.notes_path.write_text(result.notes_content, encoding="utf-8")
    return result


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert a Power BI PBIX semantic model to Snowflake Semantic View artifacts."
    )
    parser.add_argument("--pbix", required=True, help="Path to .pbix or PowerPivot .xlsx file.")
    parser.add_argument("--snowflake-database", required=True, help="Snowflake database for base tables.")
    parser.add_argument("--snowflake-schema", required=True, help="Snowflake schema for base tables.")
    parser.add_argument("--view-name", required=True, help="Generated semantic view name.")
    parser.add_argument("--output-dir", default="generated/pbix/", help="Output directory.")
    parser.add_argument("--root-table", default=None, help="Power BI table to treat as the root/fact table.")
    parser.add_argument(
        "--table-map",
        default=None,
        help="Comma-separated PowerBI=SNOWFLAKE_TABLE mappings, for example Sales=FACT_SALES,Date=DIM_DATE.",
    )
    parser.add_argument(
        "--include-hidden",
        action="store_true",
        help="Include hidden Power BI columns that are not relationship keys.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        table_map = _parse_table_map(args.table_map)
        result = convert_pbix_file(
            Path(args.pbix),
            snowflake_database=args.snowflake_database,
            snowflake_schema=args.snowflake_schema,
            view_name=args.view_name,
            root_table=args.root_table,
            table_map=table_map,
            include_hidden=args.include_hidden,
        )
        write_conversion(result, Path(args.output_dir), args.view_name)
    except Exception as exc:
        print(f"[error] {exc}", file=sys.stderr)
        return 1

    print(f"Root table: {result.root_table}", file=sys.stderr)
    print(f"YAML written -> {result.yaml_path}", file=sys.stderr)
    print(f"SQL  written -> {result.sql_path}", file=sys.stderr)
    print(f"Notes written -> {result.notes_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
