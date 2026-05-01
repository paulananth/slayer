# Semantic Model to Snowflake SQL Guardrails

Use this reference when a user asks to generate Snowflake SQL from a semantic model, verified query, or natural-language question.

Required flow:

```text
Data model or business question -> semantic model mapping -> Snowflake SQL
```

Do not bypass the semantic model when one is available.

## Required Mapping Before SQL

Before writing SQL, map the request to:

- Metric or calculation.
- Dimensions and groupings.
- Date basis and date range.
- Filters.
- Relationship path.
- Bridge/allocation rules.
- Required grain.
- Unsupported or ambiguous terms.

For non-trivial queries, include a compact mapping summary:

```text
Semantic mapping:
- Metric: positions.total_market_value_usd
- Date basis: positions.as_of_date
- Grouping: account_groups.group_name
- Filter: account_groups.group_type = 'PORTFOLIO'
- Bridge: account_group_memberships with allocation_percent and effective dates
```

## Hard Guardrails

Follow these rules strictly:

- Use only modeled metrics, dimensions, facts, filters, logical tables, and relationships.
- Do not invent a metric if the semantic model lacks one.
- Do not create a join path that is not modeled or physically supported.
- Do not use ontology meaning as a substitute for warehouse join keys.
- Do not silently pick among multiple date fields.
- Do not sum non-additive values across dates unless the question explicitly asks for a date trend.
- Do not expose private/helper fields unless the request is explicitly technical and access is appropriate.
- Do not treat near-synonyms as equivalent when the semantic model distinguishes them.
- Do not answer questions requiring data outside the semantic model.

## Clarify Instead of Guessing

Ask for clarification when:

- The requested metric name maps to multiple metrics.
- The requested date basis could be trade date, settlement date, as-of date, exposure date, issue date, maturity date, fiscal date, or calendar date.
- The requested group could mean multiple grouping types.
- The query needs an as-of date for AUM, balance, exposure, inventory, price, rate, or risk metrics.
- A bridge table can double-count and no allocation or deduplication rule is modeled.
- The relationship path is missing or many-to-many.
- Currency, unit, or timezone is ambiguous.

## Bridge and Grouping Tables

For grouping tables such as account groups:

- Treat membership as a bridge, not as a normal dimension.
- Apply effective-date predicates when the membership table has validity dates.
- Apply allocation when `allocation_percent` or equivalent exists.
- If allocation is missing and accounts can belong to multiple groups, use `COUNT(DISTINCT ...)` for counts or ask for the metric allocation rule.

Example AUM pattern:

```sql
SELECT
  ag.group_type,
  ag.group_name,
  h.as_of_date,
  SUM(h.market_value_usd * COALESCE(agm.allocation_percent, 1)) AS total_group_aum_usd
FROM holdings h
JOIN account_group_membership agm
  ON h.account_id = agm.account_id
 AND h.as_of_date >= agm.effective_from_date
 AND h.as_of_date < COALESCE(agm.effective_to_date, '9999-12-31'::DATE)
JOIN account_group ag
  ON agm.account_group_id = ag.account_group_id
WHERE ag.group_type = 'PORTFOLIO'
  AND h.as_of_date = DATE '2026-03-31'
GROUP BY ag.group_type, ag.group_name, h.as_of_date;
```

## Snowflake SQL Style

Prefer:

- Fully qualified table names when generating physical SQL.
- Semantic view logical names when generating verified-query style SQL.
- `DATE 'YYYY-MM-DD'` for date literals.
- `::DATE` casts for sentinel date constants.
- `NULLIF(denominator, 0)` in ratios.
- `COALESCE` only when the semantic definition says missing values should default.
- Clear aliases that match metric names.

Avoid:

- `SELECT *`.
- Ordinal `GROUP BY 1, 2`.
- Warehouse-specific assumptions not provided by the user.
- Joining extra tables only because names look related.

## Output Format

For generated SQL, return:

1. Semantic mapping.
2. Snowflake SQL.
3. Assumptions.
4. Missing model elements or clarifications, if any.

If the SQL cannot be generated safely, return the missing semantic-model requirements instead of SQL.

