# Semantic Modeling Skill Specification

## Purpose

This repository packages an installed Codex skill, `semantic-modeling`, for turning warehouse schemas, table groups, CSV-derived metadata, and financial-domain data models into Snowflake Semantic View artifacts and Cortex Analyst guidance.

The primary output is a governed Snowflake Semantic View YAML package. Cortex Analyst instructions, verified queries, ontology alignment notes, and Snowflake validation SQL are generated as companion artifacts.

## Installed Skill Contract

Primary skill:

- `semantic-modeling/SKILL.md`

The skill is used when a user asks Codex to design, review, convert, or generate a semantic model from:

- one denormalized table
- star schemas
- snowflake schemas
- bridge or many-to-many structures
- existing semantic-layer artifacts
- FIBO-aligned or financial-services schemas
- Snowflake warehouse metadata

Required reading order for semantic-modeling work:

1. `semantic-modeling/references/conversion-workflow.md`
2. `semantic-modeling/references/snowflake-semantic-views.md`
3. `semantic-modeling/references/fibo-ontology-alignment.md`, when financial concepts are present
4. `semantic-modeling/references/neptune-ontology-layer.md`, when Neptune or GraphRAG context is relevant
5. `semantic-modeling/references/cortex-analyst-prompting.md`
6. `semantic-modeling/references/sql-generation-guardrails.md`, when generating SQL from a semantic model

When FIBO RDF files are available locally, the separate `fibo` skill should be used to verify ontology terms from RDF/XML. If FIBO is not available, the semantic-modeling skill must preserve ontology assumptions as unverified.

## Goals

- Generate Snowflake Semantic View YAML that models logical tables, dimensions, time dimensions, facts, metrics, relationships, filters, and verified queries.
- Generate Cortex Analyst instructions separately from YAML.
- Support financial-domain semantic modeling with optional FIBO and Neptune context.
- Prevent unsafe SQL generation by requiring modeled metrics, dimensions, relationships, filters, and date assumptions.
- Provide reusable templates, references, example artifacts, and tests for repeatable semantic-modeling work.

## Non-Goals

- Do not treat ontology relationships as proof of warehouse join paths.
- Do not compute metric answers in Neptune or GraphRAG.
- Do not create or replace Snowflake semantic views unless the user explicitly requests execution.
- Do not invent metrics, joins, filters, ontology mappings, date defaults, or unsupported business definitions.
- Do not expose sensitive identifiers or row-level PII unless the semantic model is explicitly designed for that use.

## Users

Primary users:

- Data modelers building Snowflake Semantic Views.
- Analytics engineers converting warehouse tables or existing semantic layers.
- Financial-services teams aligning semantic models to FIBO-style concepts.
- Cortex Analyst implementers who need custom instructions and verified question patterns.

Secondary users:

- Reviewers validating semantic-model quality, ambiguity handling, and metric safety.
- Developers extending the schema-introspection and artifact-generation tooling.

## Core Workflows

### 1. Manual Semantic Model Design

Input:

- schema notes, DDL, ERD, CSV metadata, or existing semantic-layer artifact

Process:

- determine grain for each table
- classify tables as events, entities, snapshots, bridges, or lookup structures
- classify columns into dimensions, time dimensions, facts, metrics, filters, and private helper fields
- design relationship paths only from supported physical keys
- add verified queries for common natural-language analytics tasks
- document assumptions, unresolved questions, and validation SQL

Output:

- Snowflake Semantic View YAML
- Cortex Analyst instructions
- verified query rationale
- assumptions and model gaps
- Snowflake verify-only SQL

### 2. Automated Brainstorming From Snowflake Metadata

Input:

- Snowflake database
- one or more schemas
- optional table-name filter
- Snow CLI connection profile

Tool:

```bash
python -m tools.semantic_brainstormer \
  --database ANALYTICS \
  --schemas MART_FINANCE,MART_RISK \
  --connection myconn \
  --view-name finance_semantic_view \
  --output-dir generated/
```

Expected behavior:

- read Snow CLI connection profiles from `~/.snowflake/config.toml`
- introspect Snowflake `INFORMATION_SCHEMA`
- classify columns with deterministic suffix and datatype rules
- infer conservative relationships from LEI and `_id` patterns
- mark snapshot-like metrics as non-additive where appropriate
- generate YAML and SQL files under `generated/`
- include verify-only SQL before any create path

Outputs:

- `generated/<view_name>.yaml`
- `generated/<view_name>_create.sql`

### 3. Financial Ontology Alignment

Input:

- financial-domain warehouse schema
- optional FIBO repository or Neptune ontology service

Process:

- align terms such as legal entity, LEI, issuer, obligor, security, instrument, trade, exposure, coupon, maturity, notional amount, balance, and market value
- use ontology evidence to improve descriptions, synonyms, ambiguity handling, and verified query coverage
- keep warehouse keys and Snowflake semantic relationships authoritative for joins
- record confidence and unresolved ambiguity

Output:

- ontology alignment notes
- FIBO-style concept mappings with confidence
- role and term-disambiguation guidance for Cortex Analyst

### 4. Semantic Model to SQL

Input:

- user question
- Snowflake Semantic View YAML or equivalent model context
- optional ontology context for term disambiguation

Process:

- map the question to modeled metrics, dimensions, filters, relationships, and date basis
- ask for clarification when required fields, metrics, relationships, or defaults are missing
- generate Snowflake SQL only from the semantic model
- include a semantic mapping summary before non-trivial SQL

Output:

- semantic mapping summary
- Snowflake-compatible SQL
- assumptions, caveats, or model-gap response

### 5. Power BI PBIX Conversion

Input:

- `.pbix` or PowerPivot `.xlsx` file
- Snowflake database and schema for mapped base tables
- optional root/fact table override
- optional Power BI table to Snowflake physical table mappings

Tool:

```bash
python3 -m tools.pbixray_semantic_converter \
  --pbix ./reports/sales.pbix \
  --snowflake-database ANALYTICS \
  --snowflake-schema MART_SALES \
  --view-name sales_semantic_view \
  --output-dir generated/pbix_sales \
  --root-table Sales \
  --table-map Sales=FACT_SALES,Date=DIM_DATE
```

Expected behavior:

- use `pbixray` to inspect model tables, schema, relationships, DAX measures, calculated columns/tables, Power Query, RLS, and TMSCHEMA metadata
- select a root/fact table from active relationships, measure ownership, numeric fact columns, and table-name hints, unless `--root-table` is provided
- map Power BI tables to Snowflake logical tables and physical base tables
- map active one-to-many or many-to-one relationships to Snowflake relationship columns
- translate only safe aggregate DAX patterns into Snowflake metric expressions
- document unsupported DAX, inactive relationships, many-to-many paths, calculated tables, calculated columns, RLS, and source-mapping assumptions in conversion notes

Outputs:

- `generated/<view_name>.yaml`
- `generated/<view_name>_create.sql`
- `generated/<view_name>_conversion_notes.md`

## Repository Components

- `semantic-modeling/SKILL.md`: skill entry point and workflow contract.
- `semantic-modeling/references/`: modeling rules, Snowflake Semantic View reference, Cortex guidance, ontology alignment, Neptune architecture, and SQL guardrails.
- `semantic-modeling/assets/templates/`: reusable markdown, YAML, and SQL templates.
- `tools/schema_introspector.py`: Snowflake metadata extraction into `ColumnRecord` objects.
- `tools/column_describer.py`: deterministic column classification, descriptions, synonyms, and metric derivation.
- `tools/semantic_brainstormer.py`: CLI for generating starter Snowflake Semantic View YAML and SQL.
- `tools/pbixray_semantic_converter.py`: CLI for converting PBIX/PowerPivot semantic models into Snowflake Semantic View YAML, SQL, and conversion notes.
- `tools/snowconn_client.py`: Snow CLI profile loader and SnowConn connection wrapper.
- `examples/complex-financial-model/`: end-to-end financial semantic-layer fixture.
- `docs/neptune-semantic-model-architecture.md`: reference architecture for Neptune, GraphRAG, Snowflake, and Cortex Analyst routing.
- `tests/test_semantic_layer_artifacts.py`: fixture and reference coverage tests.

## Functional Requirements

### Input Inspection

- The system must identify table names, column names, data types, nullable flags, uniqueness signals, comments, row counts, and table types when available.
- The system must state table grain before defining metrics.
- The system must preserve explicit assumptions when metadata is incomplete.

### Column Classification

- Date and timestamp columns must become time dimensions.
- Categorical, identifier, code, status, flag, region, currency, and descriptor fields must become dimensions unless they are unsafe or not useful.
- Numeric amount, quantity, cost, balance, notional, price, rate, ratio, duration, and count fields must become facts.
- User-facing aggregate measures must be modeled as metrics, not raw facts.
- Helper facts and metrics must use private access when they are needed for calculations but should not be queried directly.

### Metric Semantics

- Additive metrics may use sums or counts where grain supports aggregation.
- Snapshot values, balances, exposures, prices, rates, ratios, and percentages must not be silently summed across dates.
- Non-additive metrics must include `non_additive_dimensions` when a time basis governs safe aggregation.
- Derived metrics must use existing modeled metrics or facts and must avoid row-level ratio errors.
- Currency, unit, null handling, fanout, and date basis must be documented when relevant.

### Relationships

- Relationship paths must be based on warehouse columns.
- The left side should normally be the foreign-key or event side.
- The right side should normally be the referenced entity side.
- Role-playing relationships must be named by business role, such as issuer, obligor, buyer, seller, broker, custodian, or counterparty.
- Many-to-many paths must require allocation, effective dating, distinct logic, or explicit model-gap handling.

### Snowflake Semantic View YAML

- YAML must use stable lowercase snake_case logical names.
- YAML must include `base_table` mappings with database, schema, and physical table name.
- YAML should include descriptions, synonyms, expressions, data types, metrics, relationships, filters, and verified queries where available.
- Legacy Cortex Analyst custom instructions must not be embedded as YAML fields.

### Cortex Analyst Instructions

- Instructions must be emitted as separate SQL clauses or copy-ready text.
- Instructions must define business context, ontology grounding, default assumptions, metric rules, ambiguity handling, unsupported question behavior, and answer style.
- Instructions must prefer semantic metrics over raw recomputation.
- Instructions must tell Cortex Analyst to clarify ambiguous financial roles and date bases.

### Neptune and GraphRAG

- Neptune is the ontology and meaning layer.
- Snowflake is the semantic model and metric execution layer.
- GraphRAG context may support term resolution, synonyms, hierarchy, and disambiguation.
- GraphRAG context must not prove warehouse data availability, create metrics, or create joins.

### Validation

- Generated SQL must include verify-only validation with `SYSTEM$CREATE_SEMANTIC_VIEW_FROM_YAML(..., TRUE)`.
- Create or replace operations must require explicit user intent.
- Tests must cover examples, references, guardrails, and architecture documents.

## Acceptance Criteria

The repository is considered healthy when:

- `python -m unittest` passes.
- The complex financial example includes Snowflake Semantic View YAML, Cortex instructions, ontology alignment notes, routing examples, SPARQL lookups, and schema SQL.
- Relationship references in example YAML point only to declared logical tables.
- Snapshot and exposure metrics are marked non-additive across their date basis.
- Cortex instructions separate SQL generation from question categorization.
- SQL guardrails explicitly prevent invented metrics, joins, filters, ontology mappings, and unsafe date defaults.
- Neptune documentation keeps ontology meaning separate from Snowflake metric execution.

## Open Risks

- Automated relationship inference is heuristic and may miss valid keys or infer weak paths when metadata is sparse.
- Suffix-based column classification needs manual review for domain-specific or poorly named columns.
- Snowflake Semantic View YAML support can change over time; official Snowflake documentation should be checked before relying on new syntax.
- FIBO mappings are only verified when local RDF evidence or Neptune ontology evidence is available.
- The current tests validate fixtures and reference coverage, not live Snowflake DDL execution.

## Future Enhancements

- Add unit tests for `tools/column_describer.py` and `tools/semantic_brainstormer.py`.
- Add a dry-run fixture that exercises the CLI without requiring Snowflake access.
- Add structured JSON output for introspected schema metadata.
- Add optional dbt, LookML, Cube, Power BI, or AtScale import adapters.
- Add stronger PII detection and exposure controls for sensitive identifiers.
- Add semantic-view linting for duplicate names, unsupported YAML keys, and missing descriptions.
