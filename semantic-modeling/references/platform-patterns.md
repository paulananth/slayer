# Cross-Platform Semantic Modeling Patterns

Use these patterns to improve judgment when converting other semantic-layer artifacts into Snowflake Semantic Views.

## Snowflake Semantic Views

Official sources:

- https://docs.snowflake.com/en/user-guide/views-semantic/overview
- https://docs.snowflake.com/en/user-guide/views-semantic/semantic-view-yaml-spec

Key concepts:

- Logical tables map to physical base tables.
- Dimensions and time dimensions provide grouping/filtering context.
- Facts are row-level quantitative helper attributes.
- Metrics are aggregate KPIs.
- Relationships connect logical tables and infer join behavior.
- Verified queries guide Cortex Analyst.
- Custom instructions are applied outside YAML.

## AtScale SML

Local reference:

- `/mnt/c/Users/paula/Downloads/s/AtScale-Semantic-Modeling-Language-v0.1.pdf`

Useful patterns:

- Repository-level control file plus object files.
- Models include relationships, metrics, calculations, perspectives, drillthroughs, aggregates, and partitions.
- Metrics distinguish additive, non-additive, and semi-additive behavior.
- Model-level relationships connect fact datasets to first-order dimensions.
- Dimension-level relationships handle embedded and snowflaked dimensions.
- Row security is a first-class modeling object.

Map to Snowflake:

- AtScale dimensions and datasets become logical tables, dimensions, time dimensions, and relationships.
- AtScale metrics/calculations become table-level or view-level metrics.
- AtScale row security should be translated into Snowflake governance/RBAC or secure modeling notes, not silently embedded as ordinary filters.

## FIBO

Local skill:

- `/mnt/c/Users/paula/.codex/skills/SKILL.md`

Useful patterns:

- OWL classes provide precise financial concepts and hierarchy.
- Object properties describe domain relationships between concepts.
- Datatype properties describe literal attributes.
- `skos:definition` is the preferred human-readable meaning.
- Multiple inheritance, restrictions, and same-IRI extension blocks matter.

Map to Snowflake:

- FIBO classes can inform logical table names, descriptions, and domain groupings.
- FIBO object properties can inform relationship names and Cortex Analyst language, but physical joins still require warehouse keys.
- FIBO datatype properties can inform dimensions, time dimensions, facts, and metric source fields.
- FIBO labels, notes, and examples can improve synonyms, descriptions, verified query wording, and custom instructions.

## dbt Semantic Layer / MetricFlow

Official sources:

- https://docs.getdbt.com/docs/build/semantic-models
- https://docs.getdbt.com/docs/build/entities
- https://docs.getdbt.com/docs/build/dimensions

Useful patterns:

- Semantic models sit on top of dbt models.
- Entities are join keys: primary, unique, foreign, and natural.
- Dimensions group and filter metrics.
- Time dimensions can define partition and SCD Type II validity behavior.
- Measures are deprecated in newer dbt specs in favor of simple metrics, but older projects may still use them.

Map to Snowflake:

- dbt entities inform Snowflake relationship columns and uniqueness assumptions.
- dbt dimensions map to Snowflake dimensions/time dimensions.
- dbt metrics map to Snowflake metrics.

## Databricks Metric Views

Official sources:

- https://docs.databricks.com/aws/en/metric-views/
- https://docs.databricks.com/aws/en/business-semantics/metric-views/yaml-reference

Useful patterns:

- Metric views define governed measures and dimensions in Unity Catalog.
- YAML includes `source`, `joins`, `dimensions`, `measures`, filters, semantic metadata, and materialization.
- Measures are aggregate expressions independent of predetermined grouping.

Map to Snowflake:

- Source maps to logical table `base_table` or a modeled source note.
- Dimensions and measures map directly.
- Joins map to Snowflake relationships.
- Semantic metadata maps to descriptions, synonyms, and custom instructions.

## Looker LookML

Official sources:

- https://docs.cloud.google.com/looker/docs/what-is-lookml
- https://docs.cloud.google.com/looker/docs/lookml-terms-and-concepts

Useful patterns:

- Models define connections, Explores, and joins.
- Views define dimensions, dimension groups, measures, and derived tables.
- Explores define user-facing query surfaces.
- LookML substitution encourages reusable definitions.

Map to Snowflake:

- Explore joins map to relationships.
- View dimensions/dimension groups map to dimensions/time dimensions.
- Measures map to metrics.
- Explore labels/descriptions map to semantic view descriptions and Cortex instructions.

## Power BI Semantic Models

Official sources:

- https://learn.microsoft.com/en-us/power-bi/connect-data/service-datasets-understand
- https://learn.microsoft.com/en-us/power-bi/personas/semantic-model-designer/

Useful patterns:

- Tables, relationships, DAX measures, hierarchies, calculation groups, RLS, and storage modes.
- Strong emphasis on star schema, business-friendly names, and reusable measures.

Map to Snowflake:

- Tables and relationships map to logical tables and relationships.
- DAX measures need SQL metric equivalents; do not transliterate blindly.
- RLS requires explicit Snowflake security design.

## Cube

Official sources:

- https://cube.dev/docs/product/data-modeling/reference/cube
- https://cube.dev/docs/product/data-modeling/reference/dimensions
- https://cube.dev/docs/product/data-modeling/reference/measures
- https://cube.dev/docs/product/data-modeling/reference/joins

Useful patterns:

- Cubes contain joins, dimensions, measures, hierarchies, segments, and access policies.
- Primary keys prevent fanout.
- Join paths and transitive joins affect metric correctness.

Map to Snowflake:

- Cubes map to logical tables.
- Measures map to metrics.
- Dimensions map to dimensions/time dimensions.
- Joins map to relationships, with fanout risks documented.
