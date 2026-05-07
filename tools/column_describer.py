"""
Classifies each ColumnRecord into dimension / time_dimension / fact / skip,
generates a business description with a sample NL question, and derives
metric definitions from fact columns.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from tools.schema_introspector import ColumnRecord

# ── Data types ────────────────────────────────────────────────────────────────

_TIME_TYPES = frozenset({
    "DATE", "TIME",
    "TIMESTAMP", "TIMESTAMP_NTZ", "TIMESTAMP_LTZ", "TIMESTAMP_TZ",
    "DATETIME",
})
_NUMERIC_TYPES = frozenset({
    "NUMBER", "NUMERIC", "DECIMAL",
    "INT", "INTEGER", "BIGINT", "SMALLINT", "TINYINT", "BYTEINT",
    "FLOAT", "FLOAT4", "FLOAT8", "DOUBLE", "DOUBLE PRECISION", "REAL",
})
_VARCHAR_TYPES = frozenset({"TEXT", "VARCHAR", "CHAR", "CHARACTER", "STRING", "NCHAR", "NVARCHAR"})
_SKIP_TYPES = frozenset({"VARIANT", "OBJECT", "ARRAY"})

# ── Classification suffixes ───────────────────────────────────────────────────

_TIME_SUFFIXES = ("_timestamp", "_datetime", "_date", "_time", "_at", "_on", "_ts", "_dt")

_FACT_SUFFIXES = (
    "_amount_usd", "_value_usd", "_notional_usd", "_balance_usd",
    "_amount", "_value", "_balance", "_notional",
    "_usd", "_local",
    "_qty", "_quantity",
    "_cost", "_fee", "_pnl", "_gain", "_loss", "_income", "_revenue", "_margin",
    "_price", "_rate", "_coupon",
    "_pct", "_percent", "_ratio", "_factor",
    "_duration", "_days", "_hours", "_lag",
    "_count", "_num",
)

_DIM_SUFFIXES = (
    "_isin", "_cusip", "_figi", "_ticker",
    "_lei", "_id", "_key", "_code",
    "_name", "_label", "_description",
    "_type", "_status", "_flag", "_category", "_class", "_group",
    "_segment", "_region", "_country", "_currency", "_ccy",
    "_version", "_source", "_system",
)

# ── Pattern table ─────────────────────────────────────────────────────────────
# (suffix, description_template, question_template, synonyms)
# Matched longest-suffix-first. {stem} = column name minus suffix, spaces.
# {table} = logical table name. {col} = raw column name lowercase.

_PATTERNS: list[tuple[str, str, str, list[str]]] = [
    # time dimensions
    ("_timestamp",    "{Stem} event timestamp.",
                      "When did the {stem} event occur?",                           ["datetime"]),
    ("_datetime",     "{Stem} date and time.",
                      "When did {stem} occur?",                                     []),
    ("_date",         "{Stem} date.",
                      "What {table} records fall on a given {stem} date?",          []),
    ("_time",         "{Stem} time of day.",
                      "At what time did {stem} occur?",                             []),
    ("_at",           "Timestamp when {stem} action was recorded.",
                      "When was the {stem} action recorded?",                       []),
    ("_on",           "Date on which {stem} occurred.",
                      "On what date did {stem} occur?",                             []),
    ("_ts",           "{Stem} timestamp.",
                      "When was {stem} recorded?",                                  []),
    ("_dt",           "{Stem} date.",
                      "What is the {stem} date?",                                   []),
    # facts — amounts (longer suffixes first)
    ("_amount_usd",   "{Stem} amount in US dollars.",
                      "What is the total {stem} amount in USD?",                    ["usd amount"]),
    ("_value_usd",    "{Stem} value in US dollars.",
                      "What is the total {stem} value in USD?",                     ["usd value"]),
    ("_notional_usd", "Notional amount in USD for {stem}.",
                      "What is the total {stem} notional in USD?",                  ["notional"]),
    ("_balance_usd",  "{Stem} balance in US dollars.",
                      "What is the total {stem} balance in USD?",                   []),
    ("_amount",       "{Stem} amount.",
                      "What is the total {stem} amount?",                           []),
    ("_value",        "{Stem} value.",
                      "What is the total {stem} value?",                            []),
    ("_balance",      "{Stem} balance. Do not sum across time.",
                      "What is the total {stem} balance?",                          []),
    ("_notional",     "Notional amount for {stem}.",
                      "What is the total {stem} notional?",                         []),
    ("_usd",          "{Stem} amount denominated in US dollars.",
                      "What is the total {stem} in USD?",                           []),
    ("_local",        "{Stem} amount in local currency.",
                      "What is the total {stem} in local currency?",                []),
    ("_quantity",     "Quantity of {stem}.",
                      "What is the total {stem} quantity?",                         ["qty"]),
    ("_qty",          "Quantity of {stem}.",
                      "What is the total {stem} quantity?",                         ["quantity"]),
    ("_cost",         "Cost of {stem}.",
                      "What is the total {stem} cost?",                             []),
    ("_fee",          "Fee charged for {stem}.",
                      "What is the total {stem} fee?",                              []),
    ("_pnl",          "Profit and loss for {stem}.",
                      "What is the total {stem} PnL?",                              ["profit and loss", "p&l"]),
    ("_gain",         "Gain amount for {stem}.",
                      "What is the total {stem} gain?",                             []),
    ("_loss",         "Loss amount for {stem}.",
                      "What is the total {stem} loss?",                             []),
    ("_income",       "Income amount for {stem}.",
                      "What is the total {stem} income?",                           []),
    ("_revenue",      "Revenue for {stem}.",
                      "What is the total {stem} revenue?",                          []),
    ("_margin",       "Margin for {stem}.",
                      "What is the total {stem} margin?",                           []),
    ("_price",        "Unit price of {stem}. Do not average unless requested.",
                      "What is the average {stem} price?",                          []),
    ("_rate",         "Rate for {stem}. Not a yield unless explicitly stated.",
                      "What is the average {stem} rate?",                           []),
    ("_coupon",       "Contractual coupon rate. Do not use as yield.",
                      "What is the average coupon rate?",                           ["coupon rate"]),
    ("_pct",          "{Stem} as a percentage. Non-additive.",
                      "What is the {stem} percentage?",                             ["percent"]),
    ("_percent",      "{Stem} as a percentage. Non-additive.",
                      "What is the {stem} percent?",                                ["pct"]),
    ("_ratio",        "{Stem} ratio. Non-additive.",
                      "What is the {stem} ratio?",                                  []),
    ("_factor",       "Scaling factor for {stem}.",
                      "What is the {stem} factor?",                                 []),
    ("_duration",     "Duration in years for {stem}.",
                      "What is the average {stem} duration?",                       []),
    ("_days",         "Number of days for {stem}.",
                      "What is the average number of {stem} days?",                 []),
    ("_hours",        "Number of hours for {stem}.",
                      "What is the average {stem} in hours?",                       []),
    ("_lag",          "Lag in days for {stem}.",
                      "What is the average {stem} lag?",                            []),
    ("_count",        "Count of {stem} items.",
                      "How many {stem} are there?",                                 ["number of", "# of"]),
    ("_num",          "Number of {stem} items.",
                      "How many {stem} are there?",                                 ["count of"]),
    # dimensions — identifiers (longer suffixes first)
    ("_isin",         "International Securities Identification Number for {stem}.",
                      "What ISIN is associated with {stem}?",                       ["ISIN"]),
    ("_cusip",        "CUSIP identifier for {stem}.",
                      "What CUSIP is associated with {stem}?",                      ["CUSIP"]),
    ("_figi",         "Financial Instrument Global Identifier for {stem}.",
                      "What FIGI is associated with {stem}?",                       ["FIGI"]),
    ("_ticker",       "Exchange ticker symbol for {stem}.",
                      "What ticker symbol is used for {stem}?",                     ["symbol", "ticker"]),
    ("_lei",          "Legal Entity Identifier for the {stem} party.",
                      "Which {stem} legal entity is involved?",                     ["LEI", "{stem} LEI"]),
    ("_id",           "Identifier for the {stem}.",
                      "Which {table} records belong to a given {stem}?",            ["{stem} identifier"]),
    ("_key",          "Surrogate key for {stem}.",
                      "Which {stem} record does this key reference?",               []),
    ("_code",         "Code representing {stem}.",
                      "Which {stem} code is used?",                                 []),
    # dimensions — descriptors
    ("_name",         "Name of the {stem}.",
                      "What are the distinct {stem} names?",                        []),
    ("_label",        "Display label for {stem}.",
                      "What label is assigned to {stem}?",                          []),
    ("_description",  "Description of {stem}.",
                      "What is the description for {stem}?",                        ["desc"]),
    ("_type",         "Type or classification of {stem}.",
                      "What types of {stem} exist?",                                ["category", "class"]),
    ("_status",       "Status of the {stem}.",
                      "What is the current {stem} status?",                         ["state"]),
    ("_flag",         "Boolean flag indicating {stem}.",
                      "Which records have {stem} flagged?",                         []),
    ("_category",     "Category of {stem}.",
                      "What categories of {stem} exist?",                           ["group", "type"]),
    ("_class",        "Classification of {stem}.",
                      "What classes of {stem} exist?",                              []),
    ("_group",        "Group of {stem}.",
                      "Which groups of {stem} exist?",                              []),
    ("_segment",      "Segment for {stem}.",
                      "Which segments exist for {stem}?",                           []),
    ("_region",       "Geographic region for {stem}.",
                      "Which regions are represented for {stem}?",                  ["geography", "area"]),
    ("_country",      "Country associated with {stem}.",
                      "Which countries appear for {stem}?",                         []),
    ("_currency",     "Currency denomination.",
                      "What currencies are used in {table}?",                       ["ccy", "denomination"]),
    ("_ccy",          "Currency denomination.",
                      "What currencies are used in {table}?",                       ["currency"]),
    ("_version",      "Version of {stem}.",
                      "Which version of {stem} is used?",                           []),
    ("_source",       "Source system for {stem}.",
                      "What source system provides {stem} data?",                   []),
    ("_system",       "System associated with {stem}.",
                      "Which system is associated with {stem}?",                    []),
    # fallback
    ("",              "{Col} in {table}.",
                      "What are the values of {col} in {table}?",                   []),
]

# ── Metric generation rules ───────────────────────────────────────────────────

# Fact suffixes that aggregate with SUM
_SUM_FACT_SUFFIXES = (
    "_amount_usd", "_value_usd", "_notional_usd", "_balance_usd",
    "_amount", "_value", "_balance", "_notional",
    "_usd", "_local",
    "_qty", "_quantity",
    "_cost", "_fee", "_pnl", "_gain", "_loss", "_income", "_revenue", "_margin",
    "_count", "_num",
)

# Fact suffixes that aggregate with AVG and are non-additive
_AVG_FACT_SUFFIXES = (
    "_price", "_rate", "_coupon",
    "_pct", "_percent", "_ratio", "_factor",
    "_duration", "_days", "_hours", "_lag",
)

# Table name keywords that indicate a snapshot grain
_SNAPSHOT_KEYWORDS = frozenset({
    "snapshot", "balance", "position", "exposure",
    "holding", "valuation", "price", "rate", "inventory",
})


# ── Output dataclasses ────────────────────────────────────────────────────────

@dataclass
class DescribedColumn:
    column: str                        # physical column name
    name: str                          # YAML field name (lowercased)
    classification: str                # dimension | time_dimension | fact | skip
    description: str
    synonyms: list[str] = field(default_factory=list)
    data_type: str = ""
    is_unique: bool = False
    expr: str = ""                     # SQL expression (= physical column name by default)


@dataclass
class MetricSpec:
    name: str
    expr: str
    description: str
    synonyms: list[str] = field(default_factory=list)
    non_additive_dimensions: list[str] = field(default_factory=list)
    access_modifier: str = "public_access"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _logical_table_name(physical: str) -> str:
    name = physical.lower()
    for prefix in ("vw_", "v_", "fact_", "dim_", "fct_", "stg_", "staging_"):
        if name.startswith(prefix):
            name = name[len(prefix):]
    return name


def _stem(col_lower: str, suffix: str) -> str:
    s = col_lower[: len(col_lower) - len(suffix)] if suffix else col_lower
    return s.replace("_", " ").strip()


def _render(template: str, col_lower: str, suffix: str, table_logical: str) -> str:
    st = _stem(col_lower, suffix)
    return (
        template
        .replace("{Stem}", st.capitalize())
        .replace("{stem}", st)
        .replace("{table}", table_logical)
        .replace("{col}", col_lower)
        .replace("{Col}", col_lower.capitalize())
    )


def _match_pattern(col_lower: str) -> tuple[str, str, str, list[str]]:
    """Return the first matching (suffix, desc_tmpl, q_tmpl, synonyms) entry."""
    for suffix, desc_tmpl, q_tmpl, syns in _PATTERNS:
        if not suffix or col_lower.endswith(suffix):
            return suffix, desc_tmpl, q_tmpl, syns
    return "", "{Col} in {table}.", "What are the values of {col} in {table}?", []


def _classify(col: ColumnRecord) -> str:
    dt = col.datatype.upper()
    name = col.column.lower()

    if dt == "BOOLEAN":
        return "dimension"
    if dt in _SKIP_TYPES:
        return "skip"
    if dt in _TIME_TYPES or any(name.endswith(s) for s in _TIME_SUFFIXES):
        return "time_dimension"
    if dt in _NUMERIC_TYPES and any(name.endswith(s) for s in _FACT_SUFFIXES):
        return "fact"
    if dt in _VARCHAR_TYPES:
        return "dimension"
    if dt in _NUMERIC_TYPES and any(name.endswith(s) for s in _DIM_SUFFIXES):
        return "dimension"
    return "skip"


def _snowflake_type(dt: str) -> str:
    """Normalise raw Snowflake data_type to a clean YAML data_type string."""
    dt = dt.upper()
    if dt in _TIME_TYPES:
        return dt
    if dt in _NUMERIC_TYPES:
        return "NUMBER"
    if dt in _VARCHAR_TYPES:
        return "VARCHAR"
    if dt == "BOOLEAN":
        return "BOOLEAN"
    return dt


# ── Public API ────────────────────────────────────────────────────────────────

def describe_column(col: ColumnRecord, table_logical: str) -> DescribedColumn:
    """Classify a column and produce its description + question string."""
    classification = _classify(col)
    col_lower = col.column.lower()
    suffix, desc_tmpl, q_tmpl, raw_syns = _match_pattern(col_lower)

    desc_sentence = _render(desc_tmpl, col_lower, suffix, table_logical)
    q_sentence = _render(q_tmpl, col_lower, suffix, table_logical)

    if col.column_comment:
        description = f"{col.column_comment.strip()} {desc_sentence} Example question: '{q_sentence}'"
    else:
        description = f"{desc_sentence} Example question: '{q_sentence}'"

    synonyms = [_render(s, col_lower, suffix, table_logical) for s in raw_syns]

    return DescribedColumn(
        column=col.column,
        name=col_lower,
        classification=classification,
        description=description,
        synonyms=synonyms,
        data_type=_snowflake_type(col.datatype),
        is_unique=col.is_unique,
        expr=col.column,
    )


def derive_metrics(
    facts: list[DescribedColumn],
    primary_time_dim: str | None,
    is_snapshot: bool,
) -> list[MetricSpec]:
    """Produce one MetricSpec per fact column, using SUM or AVG as appropriate."""
    metrics: list[MetricSpec] = []
    for dc in facts:
        name_lower = dc.name
        use_avg = any(name_lower.endswith(s) for s in _AVG_FACT_SUFFIXES)

        if use_avg:
            agg = "AVG"
            metric_name = f"avg_{name_lower}"
            non_add = [primary_time_dim] if primary_time_dim else []
        else:
            agg = "SUM"
            metric_name = f"total_{name_lower}"
            non_add = [primary_time_dim] if (is_snapshot and primary_time_dim) else []

        stem = name_lower.replace("_", " ")
        if use_avg:
            base_desc = f"Average {stem}."
            q = f"What is the average {stem}?"
        else:
            base_desc = f"Total {stem}."
            q = f"What is the total {stem}?"

        if non_add:
            base_desc += f" Do not aggregate across {non_add[0].replace('_', ' ')}."

        metrics.append(MetricSpec(
            name=metric_name,
            expr=f"{agg}({name_lower})",
            description=f"{base_desc} Example question: '{q}'",
            synonyms=dc.synonyms[:],
            non_additive_dimensions=non_add,
        ))
    return metrics


def is_snapshot_table(table_name: str) -> bool:
    low = table_name.lower()
    return any(kw in low for kw in _SNAPSHOT_KEYWORDS)
