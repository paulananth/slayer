---
name: semantic-modeling
description: Convert database tables, table groups, schemas, ERDs, CSV extracts, warehouse metadata, or ontology-aligned financial data into Snowflake Semantic View YAML and Cortex Analyst prompt/custom-instruction packages. Use when Codex needs to design, review, or generate semantic models for Snowflake from one denormalized table, a star schema, a snowflake schema, FIBO ontology concepts or RDF files, financial-domain tables, or existing semantic-layer artifacts such as AtScale SML, dbt Semantic Layer, Databricks metric views, LookML, Power BI semantic models, or Cube models.
---

# Semantic Modeling

Use this skill to turn physical data structures into Snowflake-compatible semantic views and the accompanying Cortex Analyst guidance needed for reliable natural-language analytics.

For financial-services data, combine warehouse metadata with FIBO ontology evidence when available. Use FIBO to ground business names, definitions, synonyms, class hierarchies, and relationship meaning, but keep Snowflake Semantic Views as the output format.

Snowflake Semantic Views are the default target. Treat legacy Cortex Analyst semantic model YAML and other semantic-layer formats as source or comparison material unless the user explicitly asks for a different target.

## Quick Start

1. Identify the input shape: single table, star schema, snowflake schema, existing semantic model, or partial schema notes.
2. Read `references/conversion-workflow.md` before classifying fields or proposing YAML.
3. Read `references/snowflake-semantic-views.md` before emitting Snowflake YAML or SQL.
4. For financial concepts, read `references/fibo-ontology-alignment.md` before naming entities, metrics, relationships, or prompts.
5. For Neptune/GraphRAG ontology context, read `references/neptune-ontology-layer.md` before adding graph-derived definitions, synonyms, or disambiguation.
6. Read `references/cortex-analyst-prompting.md` before writing custom instructions, synonyms, descriptions, or verified queries.
7. For semantic-model-to-SQL requests, read `references/sql-generation-guardrails.md` before writing Snowflake SQL.
8. Use templates in `assets/templates/` for final deliverables when the user asks for files or reusable artifacts.

## Required Output

For a table-to-Snowflake conversion, produce these sections unless the user asks for a narrower result:

- **Semantic View YAML**: Snowflake Semantic View YAML with logical tables, dimensions, time dimensions, facts, metrics, relationships, filters, and verified queries.
- **Ontology Alignment**: FIBO/Neptune class/property mappings, definitions used, unresolved concept ambiguity, and evidence paths or graph query references when ontology evidence was available.
- **Cortex Analyst Instructions**: custom instructions as SQL or copy-ready text, separate from YAML.
- **Verified Queries**: representative natural-language questions with SQL that proves expected usage.
- **Generated SQL**: Snowflake-compatible SQL only when grounded in modeled metrics, dimensions, filters, relationships, and assumptions.
- **Assumptions**: grain, keys, relationships, metric definitions, time zones, filters, and data gaps that were inferred.
- **Validation**: the Snowflake verify-only command to run when a Snowflake connection is available.

## Modeling Workflow

### 1. Inspect Inputs

Collect or infer:

- Fully qualified table names and columns.
- Data types, nullable flags, primary keys, foreign keys, uniqueness, and row counts if available.
- Sample values for categorical fields and business labels.
- Grain for each table: event, transaction line, order, account snapshot, customer, product, date, or another entity.
- Known business definitions for KPIs.

If the schema is incomplete, use `assets/templates/modeling-intake.md` as the checklist and proceed with explicit assumptions when reasonable.

### 2. Align Ontology When Useful

Use FIBO alignment when the data contains financial-domain concepts such as legal entities, securities, loans, derivatives, corporate actions, market data, financial instruments, rates, identifiers, agreements, accounts, transactions, or regulatory classifications.

When a FIBO repository is available:

- Use the `$fibo` skill workflow: search `.rdf` files with `rg`, resolve imports with `catalog-v001.xml`, and verify definitions from RDF/XML rather than memory.
- Map candidate table names and columns to FIBO classes, object properties, datatype properties, named individuals, labels, and definitions.
- Prefer `skos:definition` for descriptions; use `rdfs:label`, `skos:note`, and `skos:example` as supporting evidence.
- Preserve uncertainty when mappings are inferred from labels or restrictions rather than directly defined.
- Record ontology mappings in the final output and cite local RDF file paths.

If FIBO is not available locally, proceed with generic financial modeling and state that ontology mappings are unverified.

If Neptune is available as an ontology service, use it for term resolution and GraphRAG context only. Neptune can enrich meaning, synonyms, hierarchy, and disambiguation; Snowflake remains the metric and SQL execution layer.

### 3. Classify Tables and Columns

Classify each logical table as a business entity or event source. Prefer a simple star schema when possible.

Classify columns:

- **Dimensions**: categorical descriptors used for grouping, filtering, or labels.
- **Time dimensions**: dates/timestamps used for time grouping, filtering, or metric time logic.
- **Facts**: row-level numeric amounts, quantities, counts, costs, durations, balances, or helper values.
- **Metrics**: aggregate expressions over facts or rows, such as `SUM(amount)`, `COUNT(*)`, `COUNT(DISTINCT customer_id)`, ratios, and derived KPIs.
- **Filters**: common reusable predicates, such as active customers or completed orders.
- **Private helper fields**: intermediate facts or metrics needed for calculations but not intended for direct user querying.

Use ontology alignment to improve classification:

- FIBO classes often become logical tables or dimensions.
- FIBO datatype properties often become dimensions, time dimensions, or facts depending on type and use.
- FIBO object properties often inform Snowflake relationships or semantic descriptions.
- FIBO named individuals can become enumerated values, sample values, or clarification vocabulary.
- Neptune GraphRAG context can explain terms and retrieve related ontology concepts, but it must not create unmodeled metrics or warehouse joins.

### 4. Design Relationships

For multi-table inputs:

- Put the foreign-key side in `left_table` and the referenced table in `right_table`.
- Use `relationship_columns` only; Snowflake Semantic Views infer relationship type.
- Avoid many-to-many relationships unless a bridge table and metric behavior are clear.
- If multiple paths exist between tables, name relationships clearly and use metric-level `using_relationships` where needed.
- For FIBO-grounded models, use ontology property meaning to name relationships, but do not create Snowflake joins that are not supported by physical keys.

### 5. Write Snowflake YAML

Use business-friendly names, concise descriptions, and synonyms users are likely to ask. Include `data_type` for fields when known.

Prefer:

- Table-level metrics for metrics scoped to one logical table.
- View-level derived metrics for cross-table or reusable metric arithmetic.
- `access_modifier: private_access` for helper facts or intermediate metrics.
- `non_additive_dimensions` for balances, inventory snapshots, rates, ratios, or any metric that cannot be safely summed across time or another dimension.
- `verified_queries` for the most important question patterns.
- FIBO-sourced definitions in descriptions when they clarify financial meaning.
- FIBO labels, common abbreviations, and source-system terms in synonyms when they are true equivalents.

### 6. Write Cortex Analyst Instructions

Custom instructions are not part of Snowflake Semantic View YAML. Provide them separately as SQL or copy-ready text. They should:

- State the business domain and intended users.
- Define the default date, currency, timezone, and filter assumptions.
- Prefer semantic metrics over recomputing raw SQL.
- Use ontology-grounded terms where available, including FIBO-backed definitions for financial concepts.
- Clarify ambiguous terms and synonyms.
- Require clarification when a question needs unavailable data.
- Avoid fabricating definitions, ontology mappings, or joining paths not present in the semantic view.

### 7. Validate

When a Snowflake connection is available, recommend verify-only validation:

```sql
SELECT SYSTEM$CREATE_SEMANTIC_VIEW_FROM_YAML(
  '<database>.<schema>',
  $$<semantic view YAML>$$,
  TRUE
);
```

If validation fails, fix the YAML first, then re-run verification. Do not execute create/replace DDL unless the user explicitly asks.

### 8. Generate Snowflake SQL From a Semantic Model

When the user asks for `Data Model -> Semantic Model -> Snowflake SQL`, generate SQL only after mapping the question to modeled fields:

- Use only declared logical tables, dimensions, time dimensions, facts, metrics, filters, and relationships.
- Do not invent metrics, joins, filters, ontology mappings, or date defaults.
- If a metric, dimension, relationship path, date basis, grouping type, or allocation rule is missing, ask for clarification or state the model gap.
- For balances, AUM, exposure, prices, rates, ratios, and snapshot values, require a date basis or use an explicit semantic-model default.
- For bridge/grouping tables, prevent double-counting with modeled allocation, effective-date filters, or distinct logic.
- Include a short mapping summary before SQL for non-trivial queries.

Read `references/sql-generation-guardrails.md` and use `assets/templates/semantic-sql-request.md` for reusable prompts.

### 9. Use Neptune and GraphRAG

When Neptune is part of the architecture:

- Use Neptune RDF/SPARQL as the ontology service of record for FIBO and internal vocabulary.
- Use GraphRAG to retrieve definitions, synonyms, hierarchy, and related concepts before mapping a user question.
- Route meaning/disambiguation questions to Neptune context; route numeric metric questions to Snowflake through the semantic model.
- Do not query Neptune for AUM, exposure, balances, counts, or metric answers.
- Do not infer Snowflake joins from Neptune ontology relationships unless the semantic model and warehouse keys support them.

Read `references/neptune-ontology-layer.md` and `docs/neptune-semantic-model-architecture.md` for the architecture.

## References

- Snowflake target format: `references/snowflake-semantic-views.md`
- Conversion rules: `references/conversion-workflow.md`
- FIBO ontology alignment: `references/fibo-ontology-alignment.md`
- Neptune ontology layer: `references/neptune-ontology-layer.md`
- Cortex Analyst instructions: `references/cortex-analyst-prompting.md`
- SQL generation guardrails: `references/sql-generation-guardrails.md`
- Cross-platform patterns: `references/platform-patterns.md`
- Best practices: `references/best-practices.md`
- Strong examples: `references/best-examples.md`
- Test coverage: `references/test-results.md`
