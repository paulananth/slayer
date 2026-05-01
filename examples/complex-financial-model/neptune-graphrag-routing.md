# Neptune GraphRAG Routing Examples

## Example 1: Meaning Before SQL

User question:

```text
Is issuer the same as counterparty?
```

Routing:

- Use Neptune/SPARQL or GraphRAG context.
- Return definitions and role distinctions.
- Do not generate Snowflake SQL unless the user asks for a metric.

Expected response:

```text
Issuer and counterparty are distinct modeled roles. Issuer is associated with the financial instrument; counterparty is associated with trade or exposure records. They may refer to legal entities represented by LEI, but they should not be treated as interchangeable.
```

## Example 2: AUM by Account Group

User question:

```text
What is total AUM by portfolio group as of 2026-03-31?
```

Routing:

- Neptune can clarify AUM and account group vocabulary if needed.
- Snowflake semantic model supplies metric, bridge, date basis, and allocation rule.
- Generate Snowflake SQL only from modeled fields.

Semantic mapping:

```text
Metric: positions.total_market_value_usd or total_group_aum_usd
Date basis: positions.as_of_date
Grouping: account_groups.group_name
Filter: account_groups.group_type = 'PORTFOLIO'
Bridge: account_group_memberships using allocation_percent and effective dates
```

## Example 3: Ontology Relationship Without Warehouse Join

User question:

```text
Show AUM by ultimate parent of issuer.
```

Routing:

- Neptune may know parent/legal-entity hierarchy.
- If ultimate parent is not modeled or materialized in Snowflake, do not invent a join.
- Return a model gap and recommend adding an issuer-parent bridge or enrichment table in Snowflake.

Expected model-gap response:

```text
The ontology can describe legal entity hierarchy, but the semantic model does not expose an ultimate-parent relationship or Snowflake table for issuer hierarchy. Add a modeled issuer_parent relationship or materialized legal_entity_hierarchy table before generating SQL.
```

