"""
Relationship inference for Snowflake semantic-model generation.

The public routine in this module is intentionally conservative. It can use
explicit relationships from a source model, such as Power BI, and it can infer
candidate relationships from table/column metadata when keys are not declared.

Rules:
  - Explicit active relationships win.
  - Many-to-many and inactive relationships are reported, not silently modeled.
  - Inferred relationships need enough naming/key evidence to avoid guessing.
  - Tied candidates are treated as ambiguous and skipped.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass(frozen=True)
class InferenceColumn:
    name: str
    physical_name: str = ""
    data_type: str = ""
    is_unique: bool = False
    classification: str = "dimension"
    is_hidden: bool = False


@dataclass(frozen=True)
class InferenceTable:
    logical_name: str
    source_name: str = ""
    physical_name: str = ""
    columns: list[InferenceColumn] = field(default_factory=list)


@dataclass(frozen=True)
class ExplicitRelationship:
    from_table: str
    from_column: str
    to_table: str
    to_column: str
    is_active: bool = True
    cardinality: str = ""
    from_key_count: int | None = None
    to_key_count: int | None = None
    source: str = "model"


@dataclass(frozen=True)
class InferredRelationship:
    name: str
    left_table: str
    right_table: str
    left_column: str
    right_column: str
    confidence: int
    source: str
    reason: str


@dataclass(frozen=True)
class RelationshipInferenceResult:
    relationships: list[InferredRelationship]
    warnings: list[str]


_ID_SUFFIXES = ("id", "key", "code", "number", "num")
_ROLE_TO_ENTITY = {
    "buyer": {"party", "parties", "customer", "customers", "legal_entity", "legal_entities"},
    "seller": {"party", "parties", "customer", "customers", "legal_entity", "legal_entities"},
    "broker": {"party", "parties", "legal_entity", "legal_entities"},
    "custodian": {"party", "parties", "legal_entity", "legal_entities"},
    "issuer": {"party", "parties", "legal_entity", "legal_entities", "entity", "entities"},
    "obligor": {"party", "parties", "legal_entity", "legal_entities", "entity", "entities"},
    "counterparty": {"party", "parties", "legal_entity", "legal_entities"},
    "borrower": {"party", "parties", "customer", "customers", "legal_entity", "legal_entities"},
    "lender": {"party", "parties", "legal_entity", "legal_entities"},
    "payer": {"party", "parties", "customer", "customers", "legal_entity", "legal_entities"},
    "payee": {"party", "parties", "customer", "customers", "legal_entity", "legal_entities"},
}
_GENERIC_KEY_COLUMNS = {"id", "key", "code", "lei", "name"}
_DIM_HINTS = {
    "dim",
    "date",
    "calendar",
    "customer",
    "customers",
    "product",
    "products",
    "account",
    "accounts",
    "party",
    "parties",
    "entity",
    "entities",
    "legal_entity",
    "legal_entities",
    "instrument",
    "instruments",
    "security",
    "securities",
}
_FACT_HINTS = {
    "fact",
    "sales",
    "orders",
    "order_lines",
    "transactions",
    "events",
    "trades",
    "positions",
    "holdings",
    "balances",
    "exposures",
}


def _norm(name: str) -> str:
    spaced = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", str(name).strip())
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", spaced)
    clean = re.sub(r"[^0-9A-Za-z]+", "_", spaced)
    return re.sub(r"_+", "_", clean).strip("_").lower()


def _strip_table_prefix(name: str) -> str:
    norm = _norm(name)
    for prefix in ("vw_", "v_", "fact_", "fct_", "dim_", "d_", "stg_", "staging_"):
        if norm.startswith(prefix):
            return norm[len(prefix):]
    return norm


def _singular(name: str) -> str:
    name = _strip_table_prefix(name)
    if name.endswith("ies") and len(name) > 3:
        return name[:-3] + "y"
    if name.endswith("ses") and len(name) > 3:
        return name[:-2]
    if name.endswith("s") and not name.endswith("ss"):
        return name[:-1]
    return name


def _plural(name: str) -> str:
    name = _norm(name)
    if name.endswith("s"):
        return name
    if name.endswith("y") and len(name) > 1:
        return name[:-1] + "ies"
    if name.endswith(("x", "z", "ch", "sh")):
        return name + "es"
    return name + "s"


def _aliases(name: str) -> set[str]:
    norm = _strip_table_prefix(name)
    singular = _singular(norm)
    plural = _plural(singular)
    return {norm, singular, plural}


def _column_aliases(column: InferenceColumn) -> set[str]:
    names = {column.name}
    if column.physical_name:
        names.add(column.physical_name)
    aliases = {_norm(name) for name in names if name}
    expanded = set(aliases)
    for alias in aliases:
        parts = alias.split("_")
        if len(parts) > 1 and parts[-1] in _ID_SUFFIXES:
            prefix = "_".join(parts[:-1])
            expanded.add(prefix)
            expanded.add(f"{prefix}_id")
            expanded.add(f"{prefix}_key")
        if alias == "lei":
            expanded.add("legal_entity_identifier")
    return expanded


def _base_column_role(column_name: str) -> tuple[str, str]:
    norm = _norm(column_name)
    parts = norm.split("_")
    if len(parts) > 1 and parts[-1] in _ID_SUFFIXES:
        return "_".join(parts[:-1]), parts[-1]
    if norm.endswith("_lei"):
        return norm[:-4], "lei"
    return norm, ""


def _table_by_any_name(tables: list[InferenceTable]) -> dict[str, InferenceTable]:
    result: dict[str, InferenceTable] = {}
    for table in tables:
        for name in (table.logical_name, table.source_name, table.physical_name):
            if name:
                result[_norm(name)] = table
    return result


def _column_by_any_name(table: InferenceTable, raw_column: str) -> InferenceColumn | None:
    raw = _norm(raw_column)
    for column in table.columns:
        if raw in _column_aliases(column):
            return column
    return None


def _table_kind(table: InferenceTable) -> str:
    aliases = _aliases(table.logical_name) | _aliases(table.source_name) | _aliases(table.physical_name)
    if aliases & _FACT_HINTS:
        return "fact"
    if aliases & _DIM_HINTS:
        return "dimension"
    fact_like = sum(
        1
        for column in table.columns
        if column.data_type.upper() == "NUMBER"
        and not _norm(column.name).endswith(("_id", "_key"))
    )
    unique_like = sum(1 for column in table.columns if column.is_unique)
    if fact_like >= 2 and unique_like <= 1:
        return "fact"
    if unique_like:
        return "dimension"
    return "unknown"


def _looks_like_key(column: InferenceColumn) -> bool:
    name = _norm(column.name)
    return (
        column.is_unique
        or name == "lei"
        or name.endswith(("_id", "_key", "_code", "_number", "_num", "_lei"))
        or name in _GENERIC_KEY_COLUMNS
    )


def _relationship_name(
    left_table: InferenceTable,
    right_table: InferenceTable,
    left_column: InferenceColumn,
    source: str,
) -> str:
    if source == "explicit":
        return f"{left_table.logical_name}_to_{right_table.logical_name}"

    role, suffix = _base_column_role(left_column.name)
    right_aliases = _aliases(right_table.logical_name) | _aliases(right_table.source_name)
    role_is_table = bool(role and role in right_aliases)
    if role and not role_is_table and suffix in {"id", "key", "lei"}:
        return f"{left_table.logical_name}_to_{_plural(role)}"
    return f"{left_table.logical_name}_to_{right_table.logical_name}"


def _explicit_orientation(
    relationship: ExplicitRelationship,
) -> tuple[str, str, str, str] | None:
    card = re.sub(r"[^a-z]", "", relationship.cardinality.lower())
    if "manytomany" in card:
        return None
    if "manytoone" in card:
        return (
            relationship.from_table,
            relationship.from_column,
            relationship.to_table,
            relationship.to_column,
        )
    if "onetomany" in card:
        return (
            relationship.to_table,
            relationship.to_column,
            relationship.from_table,
            relationship.from_column,
        )
    if "onetoone" in card:
        return (
            relationship.from_table,
            relationship.from_column,
            relationship.to_table,
            relationship.to_column,
        )
    if relationship.from_key_count is not None and relationship.to_key_count is not None:
        if relationship.from_key_count >= relationship.to_key_count:
            return (
                relationship.from_table,
                relationship.from_column,
                relationship.to_table,
                relationship.to_column,
            )
        return (
            relationship.to_table,
            relationship.to_column,
            relationship.from_table,
            relationship.from_column,
        )
    return (
        relationship.from_table,
        relationship.from_column,
        relationship.to_table,
        relationship.to_column,
    )


def _explicit_candidates(
    tables: list[InferenceTable],
    explicit_relationships: list[ExplicitRelationship],
) -> tuple[list[InferredRelationship], list[str]]:
    by_name = _table_by_any_name(tables)
    result: list[InferredRelationship] = []
    warnings: list[str] = []

    for relationship in explicit_relationships:
        if not relationship.is_active:
            warnings.append(
                f"Skipped inactive {relationship.source} relationship "
                f"{relationship.from_table}.{relationship.from_column} -> "
                f"{relationship.to_table}.{relationship.to_column}."
            )
            continue

        oriented = _explicit_orientation(relationship)
        if oriented is None:
            warnings.append(
                f"Skipped many-to-many {relationship.source} relationship "
                f"{relationship.from_table}.{relationship.from_column} -> "
                f"{relationship.to_table}.{relationship.to_column}; model bridge/allocation rules first."
            )
            continue

        left_table_name, left_column_name, right_table_name, right_column_name = oriented
        left_table = by_name.get(_norm(left_table_name))
        right_table = by_name.get(_norm(right_table_name))
        if left_table is None or right_table is None:
            warnings.append(
                f"Skipped {relationship.source} relationship {left_table_name}.{left_column_name} -> "
                f"{right_table_name}.{right_column_name}; one or both tables were not modeled."
            )
            continue

        left_column = _column_by_any_name(left_table, left_column_name)
        right_column = _column_by_any_name(right_table, right_column_name)
        if left_column is None or right_column is None:
            warnings.append(
                f"Skipped {relationship.source} relationship {left_table_name}.{left_column_name} -> "
                f"{right_table_name}.{right_column_name}; one or both columns were not modeled."
            )
            continue

        result.append(
            InferredRelationship(
                name=_relationship_name(left_table, right_table, left_column, "explicit"),
                left_table=left_table.logical_name,
                right_table=right_table.logical_name,
                left_column=left_column.name,
                right_column=right_column.name,
                confidence=100,
                source="explicit",
                reason=f"Active relationship from {relationship.source}.",
            )
        )

    return result, warnings


def _score_inferred_pair(
    left_table: InferenceTable,
    left_column: InferenceColumn,
    right_table: InferenceTable,
    right_column: InferenceColumn,
) -> tuple[int, str] | None:
    left_name = _norm(left_column.name)
    right_name = _norm(right_column.name)
    left_role, left_suffix = _base_column_role(left_name)
    right_role, right_suffix = _base_column_role(right_name)
    left_table_aliases = _aliases(left_table.logical_name) | _aliases(left_table.source_name)
    right_table_aliases = _aliases(right_table.logical_name) | _aliases(right_table.source_name)
    left_kind = _table_kind(left_table)
    right_kind = _table_kind(right_table)
    score = 0
    reasons: list[str] = []

    if not _looks_like_key(left_column) or not _looks_like_key(right_column):
        return None
    if left_column.is_unique and right_column.is_unique and left_kind != "fact":
        return None

    if left_name == right_name:
        score += 56
        reasons.append("matching key column name")
    elif right_name in {"id", "key"} and left_role in right_table_aliases:
        score += 52
        reasons.append("foreign key prefix matches referenced table")
    elif right_name in {f"{_singular(right_table.logical_name)}_id", f"{_singular(right_table.logical_name)}_key"} and left_role in right_table_aliases:
        score += 52
        reasons.append("foreign key prefix matches referenced table key")
    elif left_role and left_role == right_role and left_suffix and right_suffix:
        score += 48
        reasons.append("matching key role")
    elif left_suffix == "lei" and right_name == "lei":
        score += 55
        reasons.append("LEI role key maps to LEI reference table")
    elif left_role in _ROLE_TO_ENTITY and right_table_aliases & _ROLE_TO_ENTITY[left_role]:
        score += 48
        reasons.append(f"role-playing key '{left_role}' maps to generic entity table")
    else:
        return None

    if right_column.is_unique:
        score += 24
        reasons.append("referenced column is unique")
    elif right_name in {"id", "key", "lei"} or right_name.endswith(("_id", "_key")):
        score += 8
        reasons.append("referenced column is key-like")

    if left_kind == "fact" and right_kind == "dimension":
        score += 12
        reasons.append("fact-to-dimension table shape")
    elif right_kind == "dimension":
        score += 6
        reasons.append("referenced table looks dimensional")

    if left_column.is_unique and right_column.is_unique:
        score -= 12
        reasons.append("both sides look unique")
    if right_table.logical_name in left_table_aliases:
        score -= 30

    if score < 70:
        return None
    return score, "; ".join(reasons)


def _inferred_candidates(tables: list[InferenceTable]) -> list[InferredRelationship]:
    candidates: list[InferredRelationship] = []
    for left_table in tables:
        for right_table in tables:
            if left_table.logical_name == right_table.logical_name:
                continue
            for left_column in left_table.columns:
                for right_column in right_table.columns:
                    scored = _score_inferred_pair(left_table, left_column, right_table, right_column)
                    if scored is None:
                        continue
                    score, reason = scored
                    candidates.append(
                        InferredRelationship(
                            name=_relationship_name(left_table, right_table, left_column, "inferred"),
                            left_table=left_table.logical_name,
                            right_table=right_table.logical_name,
                            left_column=left_column.name,
                            right_column=right_column.name,
                            confidence=score,
                            source="inferred",
                            reason=reason,
                        )
                    )
    return candidates


def infer_relationships(
    tables: list[InferenceTable],
    explicit_relationships: list[ExplicitRelationship] | None = None,
    *,
    include_inferred: bool = True,
    ambiguity_margin: int = 4,
) -> RelationshipInferenceResult:
    """Return safe relationship candidates plus warnings.

    Ambiguity is resolved per left table/column. If two candidate right sides are
    within `ambiguity_margin` points of each other, the relationship is skipped
    and reported for manual review.
    """
    explicit, warnings = _explicit_candidates(tables, explicit_relationships or [])
    chosen: list[InferredRelationship] = []
    seen_edges: set[tuple[str, str, str, str]] = set()
    explicit_left_keys: set[tuple[str, str]] = set()
    blocked_left_keys: set[tuple[str, str]] = set()
    by_any_name = _table_by_any_name(tables)

    for relationship in explicit_relationships or []:
        if relationship.is_active and _explicit_orientation(relationship) is not None:
            continue
        for table_name, column_name in (
            (relationship.from_table, relationship.from_column),
            (relationship.to_table, relationship.to_column),
        ):
            table = by_any_name.get(_norm(table_name))
            if table is None:
                continue
            column = _column_by_any_name(table, column_name)
            if column is not None:
                blocked_left_keys.add((table.logical_name, column.name))

    for relationship in explicit:
        key = (
            relationship.left_table,
            relationship.right_table,
            relationship.left_column,
            relationship.right_column,
        )
        if key in seen_edges:
            continue
        seen_edges.add(key)
        explicit_left_keys.add((relationship.left_table, relationship.left_column))
        chosen.append(relationship)

    if not include_inferred:
        return RelationshipInferenceResult(chosen, warnings)

    grouped: dict[tuple[str, str], list[InferredRelationship]] = {}
    for candidate in _inferred_candidates(tables):
        edge = (
            candidate.left_table,
            candidate.right_table,
            candidate.left_column,
            candidate.right_column,
        )
        if edge in seen_edges or (candidate.left_table, candidate.left_column) in explicit_left_keys:
            continue
        if (candidate.left_table, candidate.left_column) in blocked_left_keys:
            continue
        grouped.setdefault((candidate.left_table, candidate.left_column), []).append(candidate)

    for (left_table, left_column), candidates in sorted(grouped.items()):
        candidates.sort(key=lambda item: (-item.confidence, item.right_table, item.right_column))
        best = candidates[0]
        tied = [
            candidate
            for candidate in candidates[1:]
            if best.confidence - candidate.confidence <= ambiguity_margin
        ]
        if tied:
            targets = ", ".join(
                f"{candidate.right_table}.{candidate.right_column} ({candidate.confidence})"
                for candidate in [best] + tied
            )
            warnings.append(
                f"Skipped ambiguous relationship for {left_table}.{left_column}; candidates: {targets}."
            )
            continue
        edge = (best.left_table, best.right_table, best.left_column, best.right_column)
        if edge not in seen_edges:
            seen_edges.add(edge)
            chosen.append(best)

    return RelationshipInferenceResult(chosen, warnings)
