# Snowflake Semantic Views Reference

Primary official sources:

- Snowflake Semantic Views overview: https://docs.snowflake.com/en/user-guide/views-semantic/overview
- Snowflake Semantic View YAML specification: https://docs.snowflake.com/en/user-guide/views-semantic/semantic-view-yaml-spec
- SQL commands for semantic views: https://docs.snowflake.com/en/user-guide/views-semantic/sql
- `CREATE SEMANTIC VIEW`: https://docs.snowflake.com/en/sql-reference/sql/create-semantic-view
- `SYSTEM$CREATE_SEMANTIC_VIEW_FROM_YAML`: https://docs.snowflake.com/en/sql-reference/stored-procedures/system_create_semantic_view_from_yaml
- `SYSTEM$READ_YAML_FROM_SEMANTIC_VIEW`: https://docs.snowflake.com/en/sql-reference/functions/system_read_yaml_from_semantic_view

## Target Format

Use Snowflake Semantic Views as the default output. They are schema-level metadata objects that define business concepts over physical data and are queryable by Cortex Analyst and SQL.

Legacy Cortex Analyst semantic model YAML files on stages are still useful for migration and comparison, but Snowflake recommends Semantic Views for new work.

## YAML Shape

Top-level concepts:

- `name`: semantic view name.
- `description`: business explanation of the view.
- `tables`: logical tables mapped to physical base tables.
- `relationships`: joins between logical tables.
- top-level `metrics`: derived metrics scoped to the semantic view.
- `verified_queries`: examples of natural-language questions and SQL answers.

Logical table fields:

- `base_table`: `database`, `schema`, and `table`.
- `dimensions`: categorical attributes. Include `name`, `description`, `expr`, `data_type`, and useful `synonyms`.
- `time_dimensions`: date/time attributes. Include timezone or calendar assumptions in descriptions.
- `facts`: row-level quantitative attributes. Use `private_access` for helper values.
- `metrics`: aggregate business measures scoped to one logical table.
- `filters`: reusable predicates.

Relationship fields:

- `name`: stable join-path name.
- `left_table`: usually the fact or foreign-key side.
- `right_table`: usually the dimension or referenced side.
- `relationship_columns`: list of `left_column` and `right_column` pairs.

Snowflake Semantic Views do not require legacy `join_type` or `relationship_type`; the type is inferred from data and keys.

## Modeling Guidance

Use logical tables for business entities such as customers, orders, products, accounts, policies, claims, subscriptions, or transactions.

Use dimensions for attributes that answer "who", "what", "where", and "when". Mark dimensions with `is_enum: true` only when sample values are effectively the full set of allowed values.

Use facts for row-level quantities, amounts, prices, durations, costs, balances, and helper expressions. Facts are not the primary user-facing interface; metrics and dimensions are.

Use metrics for aggregations and KPIs. Examples:

```yaml
metrics:
  - name: total_revenue
    description: "Total recognized revenue before refunds."
    expr: SUM(net_amount)
    synonyms: ["sales", "revenue", "net sales"]
```

Use derived metrics at the view level when the expression combines metrics or spans logical tables:

```yaml
metrics:
  - name: gross_margin_rate
    description: "Gross margin divided by net revenue."
    expr: orders.gross_margin / orders.net_revenue
    access_modifier: public_access
```

Use `access_modifier: private_access` for helper facts and metrics:

```yaml
facts:
  - name: internal_cost
    description: "Internal row-level cost used for margin calculations."
    expr: unit_cost * quantity
    data_type: NUMBER
    access_modifier: private_access
```

Use `non_additive_dimensions` when a metric cannot be safely summed across a dimension. Common cases:

- Account balances across time.
- Inventory on hand across time.
- Rates, ratios, averages, and percentages.
- Distinct counts when pre-aggregation semantics are unclear.

## Verified Queries

Verified queries are documentation and steering examples for Cortex Analyst. Include the most important question patterns:

- top-N by a metric
- metric by time period
- metric by key dimension
- filtered metric
- derived metric
- ambiguous term example when useful

Use SQL that demonstrates the semantic view contract. Keep examples focused and correct.

## Validation

Use verify-only mode before applying a semantic view:

```sql
SELECT SYSTEM$CREATE_SEMANTIC_VIEW_FROM_YAML(
  '<database>.<schema>',
  $$<semantic view YAML>$$,
  TRUE
);
```

Only create or replace the semantic view when the user explicitly asks. If creating from YAML, use the same stored procedure with the third argument omitted or `FALSE`.

## Custom Instructions

Snowflake custom instructions for Cortex Analyst are not part of the Semantic View YAML. Generate them separately.

For SQL-created semantic views, use these `CREATE SEMANTIC VIEW` clauses:

- `AI_SQL_GENERATION '<instructions>'`: tells Cortex Analyst how to generate SQL.
- `AI_QUESTION_CATEGORIZATION '<instructions>'`: tells Cortex Analyst how to classify questions, reject unsupported questions, or ask for clarification.

When the semantic view is created from YAML with `SYSTEM$CREATE_SEMANTIC_VIEW_FROM_YAML`, provide a separate custom-instruction package and tell the user to apply it through `CREATE SEMANTIC VIEW` SQL or the Snowflake Semantic View Editor as appropriate for their workflow.
