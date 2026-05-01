# Semantic Modeling Intake

Use this checklist when converting tables to a Snowflake Semantic View.

## Source Tables

- Fully qualified table names:
- Table descriptions:
- Row counts:
- Refresh cadence:
- Owner or steward:

## Columns

For each table, collect:

- Column name:
- Data type:
- Nullable:
- Primary key or unique key:
- Foreign key:
- Sample values:
- Business description:

## Grain

- One row represents:
- Known duplicate conditions:
- Snapshot date or event date:

## Relationships

- Fact/event table:
- Dimension/entity tables:
- Join columns:
- Cardinality assumptions:
- Known many-to-many bridges:

## Metrics

- KPI name:
- Business definition:
- Formula:
- Date dimension:
- Filters/exclusions:
- Additive, non-additive, or semi-additive:
- Unit/currency:

## Cortex Analyst Defaults

- Intended users:
- Default date range:
- Default timezone:
- Default currency:
- Terms users commonly ask:
- Ambiguous terms:
- Questions the model should answer:
- Questions the model should refuse or clarify:

## Ontology Alignment

- Is this financial-domain data that should use FIBO?
- FIBO repository path:
- Candidate FIBO modules:
- Business terms to resolve:
- Table/column to FIBO mappings:
- Terms that are ambiguous:
- Ontology definitions that should appear in descriptions:
- Ontology terms that should become synonyms:
