# Semantic Model to Snowflake SQL Request

Use this prompt when asking Codex to generate Snowflake SQL from a semantic model.

```text
Use $semantic-modeling to read this semantic model and generate Snowflake-compatible SQL for the question below.

Rules:
- Use only modeled metrics, dimensions, filters, facts, logical tables, and relationships.
- Do not invent metrics, joins, filters, ontology mappings, or date defaults.
- If a metric, date basis, relationship path, grouping type, allocation rule, currency, or unit is ambiguous or missing, ask for clarification instead of writing unsafe SQL.
- For AUM, balances, exposure, prices, rates, ratios, inventory, or snapshot values, require an explicit as-of/date basis or use only an explicit model default.
- For grouping or bridge tables, apply modeled allocation, effective-date filters, or distinct logic to avoid double-counting.
- Provide a semantic mapping summary before the SQL.

Business question:
<question>

Semantic model:
<paste YAML or model definition>
```

