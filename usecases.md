# Semantic Modeling Skill Use Cases

## Sources Read

This guide is based on the installed project material:

- `semantic-modeling/SKILL.md`
- `semantic-modeling/references/conversion-workflow.md`
- `semantic-modeling/references/snowflake-semantic-views.md`
- `semantic-modeling/references/fibo-ontology-alignment.md`
- `semantic-modeling/references/neptune-ontology-layer.md`
- `semantic-modeling/references/cortex-analyst-prompting.md`
- `semantic-modeling/references/sql-generation-guardrails.md`
- `semantic-modeling/references/platform-patterns.md`
- `semantic-modeling/references/best-practices.md`
- `semantic-modeling/references/best-examples.md`
- `semantic-modeling/references/test-results.md`
- `semantic-modeling/assets/templates/`
- `docs/neptune-semantic-model-architecture.md`
- `examples/complex-financial-model/`
- `tests/test_semantic_layer_artifacts.py`

## Simple Explanation

Use the `semantic-modeling` skill when you have database tables, schema notes, an existing semantic model, or financial ontology context and you want a Snowflake-ready semantic layer.

In plain English, this skill helps answer:

> "How should these tables become business-friendly metrics, dimensions, joins, prompts, and safe SQL rules for Snowflake and Cortex Analyst?"

## Basic Prompt Pattern

Use this shape for most requests:

```text
Use $semantic-modeling to <what you want>.

Input:
- <tables, columns, YAML, DDL, ERD, CSV metadata, or existing semantic model>

Create:
- Snowflake Semantic View YAML
- Cortex Analyst instructions
- verified queries
- assumptions and model gaps
- verify-only Snowflake validation SQL

Special rules:
- <date defaults, currency rules, sensitive fields, FIBO terms, Neptune context, security rules>
```

## What The Skill Can Produce

| Output | What It Means |
| --- | --- |
| Snowflake Semantic View YAML | Logical tables, dimensions, time dimensions, facts, metrics, relationships, filters, and verified queries. |
| Cortex Analyst instructions | `AI_SQL_GENERATION` and `AI_QUESTION_CATEGORIZATION` guidance outside YAML. |
| Ontology alignment notes | FIBO or Neptune mappings, definitions, confidence, and unresolved ambiguity. |
| Verified queries | Example natural-language questions with SQL patterns that teach Cortex Analyst how to answer. |
| Snowflake SQL | SQL generated only from modeled metrics, dimensions, filters, and relationships. |
| Assumptions and gaps | Grain, key, date, currency, metric, join, and data-quality assumptions. |
| Validation SQL | Verify-only `SYSTEM$CREATE_SEMANTIC_VIEW_FROM_YAML(..., TRUE)` command. |

## Quick Decision Guide

| If You Have | Use The Skill To |
| --- | --- |
| One table | Build a simple semantic view with metrics, dimensions, filters, and verified queries. |
| Fact and dimension tables | Build a star-schema semantic view with relationships. |
| Normalized product/customer/account hierarchy | Build a snowflake-schema semantic view and document join paths. |
| Daily balances, positions, inventory, prices, rates, or exposure | Model non-additive metrics safely with explicit date basis. |
| Financial tables | Add FIBO-style meanings, synonyms, and ambiguity rules. |
| Neptune or GraphRAG | Use ontology context for meaning and disambiguation, not metric execution. |
| Existing dbt, LookML, Power BI, Cube, Databricks, or AtScale model | Convert semantic intent into Snowflake Semantic View YAML. |
| Power BI `.pbix` file | Extract the embedded semantic model with `pbixray`, choose a root table, and generate Snowflake Semantic View artifacts. |
| User questions against a model | Map the question to semantic fields first, then generate Snowflake SQL safely. |
| Partial schema notes | Use an intake checklist and proceed with labeled assumptions. |
| Need deployment help | Generate verify-only validation SQL, not create/replace DDL unless requested. |

## Use Cases Covered By The Installed Skill

The installed test matrix explicitly covers the following 50 use cases. These can also be combined.

### A. Build Semantic Views From Physical Tables

| # | Use Case | When To Use It | How To Ask | Main Output |
| --- | --- | --- | --- | --- |
| 1 | Single transaction table | You have one table like `orders` with IDs, dates, statuses, quantities, and amounts. | "Convert this `orders` table into Snowflake Semantic View YAML." | One logical table with dimensions, time dimensions, facts, metrics, filters, verified queries, and Cortex defaults. |
| 2 | Star schema | You have a fact table plus dimensions, such as sales, customer, product, and date. | "Model `fact_sales` with `dim_customer`, `dim_product`, and `dim_date`." | Fact-to-dimension relationships and reusable metrics. |
| 3 | Snowflake schema | Your dimensions are normalized, such as product to category to department. | "Convert this normalized product hierarchy into a semantic view." | Logical tables with supported multi-hop relationships and join assumptions. |
| 4 | Event count table | You have app, clickstream, workflow, or system events. | "Create metrics for event count, distinct users, and sessions." | Event metrics, time dimensions, and event-type groupings. |
| 5 | Degenerate dimensions | IDs like order number or invoice number live directly in the fact table. | "Expose useful order and invoice identifiers without creating extra tables." | Identifier dimensions for filtering or drill-through, not metrics. |
| 6 | Partial schema input | You only know table names and some columns. | "Use the intake checklist and make clear assumptions." | Draft semantic model plus questions and assumptions. |
| 7 | Missing primary keys | Tables do not declare PK/FK constraints. | "Infer candidate relationships but mark assumptions." | Conservative relationships and key-confidence notes. |

### B. Model Snapshot And Time-Sensitive Data

| # | Use Case | When To Use It | How To Ask | Main Output |
| --- | --- | --- | --- | --- |
| 8 | Account balance snapshot | You have balances by account and date. | "Model daily account balances without unsafe summing across dates." | Non-additive balance metrics and date-basis rules. |
| 9 | Inventory snapshot | You have inventory on hand by warehouse, SKU, and date. | "Model inventory as period-end or latest-date metrics." | Semi-additive or non-additive inventory metrics. |
| 10 | Market prices | You have price history with close, bid, ask, date, instrument, and currency. | "Model prices and clarify price type." | Price facts, careful aggregation rules, and date prompts. |
| 11 | Interest rate curves | You have curve points by tenor, rate, curve name, date, and currency. | "Model rates so users must specify tenor and date." | Non-additive rate facts and clarification rules. |
| 12 | Time zone handling | Timestamps are UTC but users ask local business questions. | "State timezone assumptions in time dimensions and instructions." | Timezone-aware descriptions and prompt defaults. |
| 13 | Fiscal calendar | Date tables include fiscal year, quarter, and period. | "Add fiscal calendar dimensions and verified queries." | Fiscal groupings and example queries. |
| 14 | Slowly changing dimensions | Attributes like customer segment change over time. | "Document validity columns and avoid unsupported point-in-time joins." | Validity assumptions and cautious relationship rules. |

### C. Financial Services And FIBO-Aligned Models

| # | Use Case | When To Use It | How To Ask | Main Output |
| --- | --- | --- | --- | --- |
| 15 | Loan portfolio | Loans, borrowers, collateral, rates, maturity dates, and balances. | "Build a loan portfolio semantic view and ground terms in FIBO." | Loan metrics, balance non-additivity, borrower and maturity definitions. |
| 16 | Bond securities | Bond master data plus positions or holdings. | "Align security, issuer, coupon, maturity, and notional to FIBO." | Instrument model with FIBO-style ontology alignment. |
| 17 | Equity holdings | Equity securities, issuers, holdings, and market values. | "Model holdings, securities, issuers, and market value by date." | Holdings metrics, issuer relationships, and date-sensitive market value. |
| 18 | Derivatives exposure | Swaps or derivatives with counterparties, notional, effective date, and maturity. | "Model notional and exposure carefully with date basis." | Exposure and notional metrics with FIBO-style terms and warnings. |
| 19 | Legal entity identifier | Tables contain LEI, legal name, jurisdiction, or registration status. | "Model LEI and legal entity fields with synonyms." | LEI dimensions and legal-entity descriptions without overclaiming uniqueness. |
| 20 | Counterparty risk | Exposures by counterparty, rating, product, and date. | "Model exposure by counterparty and clarify rating source." | Counterparty relationships, exposure date basis, and risk prompts. |
| 21 | Corporate actions | Security corporate-action events. | "Model corporate actions and event dates with FIBO-style terms." | Event dimensions, action types, dates, and ontology notes. |
| 22 | Trade lifecycle | Trades with trade date, settlement date, product, counterparty, quantity, and price. | "Model trade and settlement dates separately." | Trade metrics and date ambiguity rules. |
| 23 | Payment transactions | Payments with payer, payee, amount, channel, status, and date. | "Model payment amount and count with payer/payee roles." | Role-playing party relationships and completed/active filters. |
| 24 | FIBO class explanation | You want domain terms explained before modeling. | "Explain the FIBO concepts for bonds before creating YAML." | RDF-backed definitions and naming guidance when FIBO is available. |
| 25 | Ambiguous FIBO/local term | A local name like `Security` can mean multiple concepts. | "Map this term and show ambiguity by IRI or definition." | Disambiguation with confidence and evidence paths. |
| 26 | FIBO object property as join hint | Ontology says two concepts relate, but tables lack join keys. | "Use ontology for meaning only unless warehouse keys exist." | Description guidance without unsupported Snowflake relationships. |
| 27 | FIBO datatype property as field | A field resembles coupon rate, maturity date, LEI, or notional amount. | "Classify this field using FIBO evidence." | Field classification with ontology mapping and confidence. |

### D. Handle Business Ambiguity And Risky Modeling Areas

| # | Use Case | When To Use It | How To Ask | Main Output |
| --- | --- | --- | --- | --- |
| 28 | Many-to-many bridge | Customers to accounts, accounts to groups, products to categories, or similar bridges. | "Model this bridge and prevent double counting." | Allocation, effective-date, distinct-count, or clarification rules. |
| 29 | Role-playing dates | One table has order date, ship date, delivery date, trade date, settlement date, etc. | "Name each date role and define the default date basis." | Separate time dimensions and prompt clarification. |
| 30 | Role-playing parties | One party table is used as buyer, seller, broker, custodian, issuer, or counterparty. | "Create role-specific relationships and clarify party meaning." | Role-named relationships and ambiguity handling. |
| 31 | Ambiguous revenue | Gross revenue, net revenue, bookings, and recognized revenue all exist. | "Keep revenue metrics separate and define default usage." | Separate metrics and no false synonyms. |
| 32 | Currency conversion | Amounts exist in transaction currency and reporting currency. | "Do not mix currencies silently; document units." | Currency dimensions, unit-specific metrics, and prompt defaults. |
| 33 | Row-level security | Access must be restricted by region, legal entity, customer, or business unit. | "Document governance needs separately from analytics filters." | Security caveats and Snowflake governance notes. |
| 34 | Sensitive identifiers | Tables include SSN, tax IDs, account numbers, names, addresses, or emails. | "Flag sensitive fields and avoid exposing raw PII by default." | Private fields, refusal rules, and governance notes. |
| 35 | Unsupported question handling | Users ask for external benchmarks, forecasts, or data not in the model. | "Create refusal rules for unavailable data." | Cortex instructions that explain missing data instead of fabricating answers. |

### E. Convert Other Semantic Layers To Snowflake

| # | Use Case | When To Use It | How To Ask | Main Output |
| --- | --- | --- | --- | --- |
| 36 | dbt Semantic Layer input | You have dbt semantic models, entities, dimensions, and metrics. | "Convert this dbt semantic model to Snowflake Semantic View YAML." | Entities mapped to relationships, dimensions, and metrics. |
| 37 | Databricks metric view input | You have Databricks metric view YAML. | "Convert this Databricks metric view to Snowflake Semantic View YAML." | Source, joins, dimensions, measures, and metadata mapped to Snowflake. |
| 38 | LookML input | You have Looker models, explores, views, joins, dimensions, and measures. | "Convert this LookML into a Snowflake Semantic View." | Explores and joins mapped to relationships; measures mapped to metrics. |
| 39 | Power BI semantic model input | You have Power BI tables, relationships, DAX measures, hierarchies, or RLS. | "Translate this Power BI semantic model to Snowflake semantic-view intent." | SQL metric equivalents, relationships, hierarchy notes, and RLS caveats. |
| 40 | Cube model input | You have Cube cubes, joins, measures, dimensions, segments, or access policies. | "Convert these Cube definitions into Snowflake Semantic View YAML." | Cubes mapped to logical tables with fanout and access-policy caveats. |
| 41 | AtScale SML input | You have AtScale datasets, dimensions, metrics, calculations, relationships, or row security. | "Convert this AtScale SML model to Snowflake Semantic Views." | AtScale metrics and dimensions mapped to Snowflake with governance notes. |
| 41a | Power BI PBIX file input | You have the `.pbix` file, not exported model JSON. | "Use `tools.pbixray_semantic_converter` to convert this PBIX into Snowflake Semantic View YAML and SQL." | PBIX tables, relationships, common DAX measures, root-table notes, and validation SQL. |

### F. Cortex Analyst, Prompts, Verified Queries, And SQL

| # | Use Case | When To Use It | How To Ask | Main Output |
| --- | --- | --- | --- | --- |
| 42 | Verified query generation | You need examples that teach Cortex Analyst common questions. | "Generate verified queries for top-N, trend, filters, derived metrics, and ambiguity." | Representative natural-language questions with SQL. |
| 43 | Natural-language prompt package | You need the best prompt or instructions for users querying the model. | "Create a Cortex Analyst prompt package for this semantic model." | Business context, defaults, metric rules, ambiguity handling, and examples. |
| 44 | Semantic model to SQL | You have a user question and a semantic model. | "Map this question to the semantic model, then generate Snowflake SQL." | Semantic mapping summary, SQL, assumptions, or missing requirements. |
| 45 | Clarification instead of guessing | A question lacks metric, date, currency, grouping, or relationship details. | "Ask what is missing instead of writing unsafe SQL." | Clarifying question or model-gap response. |
| 46 | Neptune/GraphRAG meaning before SQL | A question needs ontology meaning before metric SQL. | "Resolve the term with Neptune/GraphRAG, then map to the semantic model." | Ontology context plus Snowflake mapping when available. |
| 47 | Ontology relationship without warehouse join | Graph says concepts are related, but Snowflake has no key path. | "Explain the relationship but do not invent a join." | Model-gap response and recommended warehouse materialization. |

### G. Validation, Delivery, And Automation

| # | Use Case | When To Use It | How To Ask | Main Output |
| --- | --- | --- | --- | --- |
| 48 | YAML validation command | You need to check generated YAML safely. | "Show how to validate this semantic view without creating it." | Verify-only `SYSTEM$CREATE_SEMANTIC_VIEW_FROM_YAML(..., TRUE)` SQL. |
| 49 | Generation only, no DDL | You want artifacts but no Snowflake changes. | "Generate files only; do not execute DDL." | YAML and SQL files with create blocks disabled or clearly separated. |
| 50 | Full deliverable request | You want the complete package. | "Create the full Snowflake semantic model package." | YAML, ontology alignment, Cortex instructions, verified queries, assumptions, and validation SQL. |

## Automation Use Case: Brainstorm From Live Snowflake Metadata

Use this when you want a first-pass semantic model from live Snowflake `INFORMATION_SCHEMA`.

```bash
python3 -m tools.semantic_brainstormer \
  --database ANALYTICS \
  --schemas MART_FINANCE,MART_RISK \
  --connection myconn \
  --view-name financial_risk_semantic_view \
  --output-dir generated/
```

What it does:

- connects using a Snow CLI profile
- reads table and column metadata
- classifies fields by datatype and naming patterns
- infers simple relationships
- creates starter Snowflake Semantic View YAML
- creates SQL with verify-only validation first

Important limitation:

- This is a brainstormer, not a final business approval tool. Review grain, metrics, joins, sensitive fields, and non-additive values before deployment.

## Automation Use Case: Convert A Power BI PBIX File

Use this when you have a `.pbix` or PowerPivot `.xlsx` file and want Snowflake Semantic View artifacts.

```bash
python3 -m tools.pbixray_semantic_converter \
  --pbix ./reports/sales.pbix \
  --snowflake-database ANALYTICS \
  --snowflake-schema MART_SALES \
  --view-name sales_semantic_view \
  --output-dir generated/pbix_sales \
  --root-table Sales \
  --table-map Sales=FACT_SALES,Customer=DIM_CUSTOMER,Date=DIM_DATE
```

What it does:

- uses `pbixray` to extract Power BI model tables, columns, active relationships, DAX measures, calculated columns/tables, Power Query, RLS, and TMSCHEMA metadata
- chooses a root/fact table from relationship direction, measure ownership, numeric fact-like columns, and table-name hints
- lets you override the selected root with `--root-table`
- maps Power BI tables to Snowflake physical tables with `--table-map`
- converts safe aggregate DAX patterns to Snowflake metric expressions
- writes YAML, SQL, and conversion notes with a 5-Whys decision summary

Important limitation:

- DAX is not fully equivalent to SQL. The converter only translates common aggregate patterns automatically and records unsupported DAX, RLS, calculated tables, calculated columns, inactive relationships, and many-to-many paths for manual review.

## Best Request Examples

### Financial Holdings

```text
Use $semantic-modeling to convert these Snowflake tables into a semantic view:
- MART.HOLDINGS.POSITION(position_id, security_id, account_id, as_of_date, quantity, market_value_usd, book_value_usd)
- MART.HOLDINGS.SECURITY(security_id, isin, cusip, issuer_lei, security_type, coupon_rate, maturity_date, currency)
- MART.REF.LEGAL_ENTITY(lei, legal_name, jurisdiction, entity_status)

Use FIBO concepts for security, issuer, legal entity identifier, coupon, maturity, and market value.
Create Snowflake Semantic View YAML, Cortex Analyst instructions, verified queries, assumptions, and validation SQL.
```

### Ambiguous Revenue

```text
Use $semantic-modeling to convert SALES.ORDER_LINE(order_line_id, order_id, customer_id, order_date, ship_date, gross_amount, discount_amount, net_amount, booking_amount, recognized_revenue, status, channel) into Snowflake Semantic View YAML.

Include Cortex Analyst instructions so users do not confuse bookings, gross revenue, net revenue, and recognized revenue.
```

### Existing Semantic Layer Migration

```text
Use $semantic-modeling to convert this LookML/dbt/Power BI/Cube/AtScale semantic model into a Snowflake Semantic View.

Preserve business metric definitions, map source dimensions and joins, add verified queries, and call out any relationship, RLS, DAX, or fanout caveats.
```

### Question To SQL

```text
Use $semantic-modeling to answer this from the semantic model:
"What is total AUM by issuer for the latest as-of date?"

First show the semantic mapping. Generate Snowflake SQL only if the metric, issuer relationship, and date basis are modeled.
```

## What Not To Use It For

Do not use this skill to:

- make up business metrics from column names alone
- create Snowflake DDL without explicit permission
- answer metric questions from Neptune or GraphRAG instead of Snowflake
- turn FIBO object properties into physical joins without warehouse keys
- silently choose among trade date, settlement date, as-of date, exposure date, issue date, or maturity date
- silently sum balances, exposures, AUM, market values, inventory, prices, rates, percentages, or ratios across dates
- treat near-synonyms as equivalent when the model distinguishes them
- expose sensitive identifiers or row-level personal data by default

## Easy Checklist Before Using The Skill

Provide as much of this as possible:

- Tables and columns
- Data types
- Primary keys and foreign keys
- Row grain for each table
- Important metrics and business definitions
- Date basis and timezone
- Currency and unit rules
- Sensitive fields and security requirements
- Existing semantic-layer files, if migrating
- FIBO, RDF, Neptune, or internal ontology context, if available
- Desired output files or sections

If some details are missing, the skill can still create a draft, but it should label assumptions clearly.
