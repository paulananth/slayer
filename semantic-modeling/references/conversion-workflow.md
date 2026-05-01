# Table-to-Semantic-View Conversion Workflow

Use this workflow when converting one table or a set of related tables to Snowflake Semantic View YAML.

For financial-domain tables, use `references/fibo-ontology-alignment.md` before final naming and descriptions. FIBO can improve semantic precision, but it does not override the warehouse schema or actual data constraints.

## 1. Determine Grain

State the grain for every logical table. Examples:

- One row per order.
- One row per order line.
- One row per customer.
- One row per account per day.
- One row per claim event.

Do not define metrics until the grain is clear. If grain is ambiguous, infer it from keys and column names, then record the assumption.

## 2. Identify Table Roles

Single table:

- Treat it as one logical table.
- If it mixes transaction and descriptive columns, expose descriptors as dimensions and numeric event values as facts/metrics.

Star schema:

- Treat the central event/transaction table as the main fact-like logical table.
- Treat lookup/entity tables as logical tables with dimensions.
- Define relationships from the event table to each entity table.

Snowflake schema:

- Keep normalized entity tables as separate logical tables when they provide reusable business concepts.
- Avoid unnecessary multi-hop paths if denormalizing a small lookup into the nearest logical table would make the model clearer.

Bridge or many-to-many:

- Ask for business intent if metric behavior changes depending on allocation.
- If proceeding, create explicit bridge logic and verified queries that prove totals do not double count.

## 3. Classify Columns

Name patterns are hints, not proof.

Dimensions:

- IDs that users group or filter by, if meaningful.
- Codes, statuses, categories, regions, channels, names, types, flags.
- Low-to-medium cardinality numeric bands or codes.

Time dimensions:

- Columns ending in `_date`, `_time`, `_timestamp`, `_at`, `_dt`.
- Add descriptions for timezone and business calendar assumptions.

Facts:

- Amounts, quantities, prices, costs, discounts, balances, durations, counts.
- Row-level expressions such as `unit_price * quantity`.

Metrics:

- `COUNT(*)` for event count.
- `COUNT(DISTINCT entity_id)` for unique entity count.
- `SUM(amount)` for additive currency/quantity.
- `AVG(value)` only when a simple row average is truly the intended KPI.
- Ratios as derived metrics from helper metrics, not averages of row-level ratios unless intended.

Private helper fields:

- Numerators and denominators used only for final metrics.
- Internal costs, raw amounts, or technical metrics that users should not query directly.

## 4. Naming Rules

Use stable, lowercase snake_case names in YAML. Use business-friendly `description` and `synonyms`.

For FIBO-aligned financial concepts, prefer names that are both warehouse-readable and business precise. Preserve common abbreviations as synonyms, not primary names, unless the abbreviation is the business standard, such as `lei`.

Prefer:

- `total_revenue`, not `sum_amt`.
- `order_count`, not `count`.
- `customer_segment`, not `c_mktsegment`.
- `gross_margin_rate`, not `gm_pct_calc`.

Avoid:

- Acronyms without explanation.
- Source-system column names as user-facing names.
- Multiple metrics with overlapping definitions unless the difference is explicit.

## 5. Relationship Rules

For each relationship:

- Confirm the left side contains the foreign key.
- Confirm the right side has unique or primary key semantics.
- Use composite keys when needed.
- Name by path, such as `orders_to_customers` or `order_lines_to_products`.

If two paths connect the same entities, describe the business meaning:

- `orders_to_order_date`
- `orders_to_ship_date`
- `orders_to_bill_to_customer`
- `orders_to_sold_to_customer`

Use verified queries to show the intended path.

## 6. Metric Design Checks

Before finalizing metrics, check:

- Additivity: Can this be summed across all dimensions and time?
- Grain: Is the numerator and denominator computed at the right level?
- Fanout: Could joins duplicate rows before aggregation?
- Null handling: Should missing values be treated as zero or excluded?
- Currency/unit: Are amounts in one currency or mixed?
- Time: Which date controls the metric?
- Filters: Should canceled, test, deleted, or inactive records be excluded?

## 7. Natural-Language Coverage

For Cortex Analyst quality, add:

- Synonyms for common business terms and abbreviations.
- FIBO-backed labels and definitions for financial terms when available.
- Descriptions that explain business meaning, not just source columns.
- Verified queries for top user intents.
- Filters for common policy decisions.
- Explicit custom instructions for ambiguity and defaults.

## 8. Deliverable Format

When producing final output, include:

1. Semantic View YAML.
2. Custom instructions SQL or text.
3. Verified query rationale.
4. Assumptions and questions.
5. Validation SQL.
