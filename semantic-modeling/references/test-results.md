# Semantic Modeling Skill Test Results

Date: 2026-05-01

Method: 50 scenario-based smoke tests were run as deterministic skill-coverage checks. Each test verifies that the skill gives a concrete workflow path, expected outputs, and relevant references/templates for the scenario. These tests do not execute Snowflake DDL and do not run 50 separate LLM sub-sessions.

Status summary: 50 passed, 0 failed.

## Test Matrix

### Test 01: Single Transaction Table

- Scenario: Convert one `orders` table with IDs, customer attributes, dates, status, quantity, and net amount.
- Expected behavior: Produce one logical table, time dimensions, facts, total/order-count metrics, filters, verified queries, and Cortex defaults.
- Coverage: `conversion-workflow.md`, `snowflake-semantic-views.md`, `semantic-view.yaml`.
- Result: PASS.

### Test 02: Star Schema Sales Model

- Scenario: Convert `fact_sales` plus `dim_customer`, `dim_product`, and `dim_date`.
- Expected behavior: Model fact-to-dimension relationships from foreign keys, keep customer/product/date as logical tables, and avoid duplicate metric definitions.
- Coverage: relationship rules, star-schema guidance, verified query guidance.
- Result: PASS.

### Test 03: Snowflake Schema Product Hierarchy

- Scenario: Convert sales with product, category, and department tables.
- Expected behavior: Preserve multi-hop dimensional context only when keys support it; document join-path assumptions.
- Coverage: snowflake schema guidance and relationship naming.
- Result: PASS.

### Test 04: Account Balance Snapshot

- Scenario: Convert account daily balances.
- Expected behavior: Treat balance as non-additive across time; add non-additive guidance and clarify default balance date.
- Coverage: `non_additive_dimensions`, Cortex ambiguity handling.
- Result: PASS.

### Test 05: Inventory Snapshot

- Scenario: Convert daily inventory on hand by warehouse and SKU.
- Expected behavior: Use inventory quantity as semi/non-additive over time; prefer latest/period-end verified queries.
- Coverage: non-additive metrics and time-dimension defaults.
- Result: PASS.

### Test 06: Event Count Table

- Scenario: Convert application events with event type, timestamp, user ID, and session ID.
- Expected behavior: Create event count, distinct user count, distinct session count, event type dimensions, and event-time defaults.
- Coverage: metric design and natural-language coverage.
- Result: PASS.

### Test 07: Subscription Revenue

- Scenario: Convert subscriptions with MRR, ARR, plan, start/end dates, and customer.
- Expected behavior: Define clear metrics for MRR/ARR, avoid equating bookings and revenue, clarify active subscription filters.
- Coverage: metric definitions, synonyms, prompt ambiguity rules.
- Result: PASS.

### Test 08: Loan Portfolio

- Scenario: Convert loans, borrowers, collateral, rates, maturity dates, and balances.
- Expected behavior: Use FIBO alignment for loan/borrower/collateral/rate/maturity terminology and non-additive balance handling.
- Coverage: `fibo-ontology-alignment.md`, non-additive metrics.
- Result: PASS.

### Test 09: Bond Securities

- Scenario: Convert bond master and position tables.
- Expected behavior: Align security, issuer, coupon, maturity, notional, and position terms to FIBO when RDF evidence is available.
- Coverage: FIBO modules SEC/FBC/MD and ontology output section.
- Result: PASS.

### Test 10: Equity Holdings

- Scenario: Convert equity securities, issuers, holdings, and market values.
- Expected behavior: Model holdings as fact-like, securities and issuers as dimensions/entities, and market value as date-sensitive.
- Coverage: FIBO alignment, relationship design, time dimensions.
- Result: PASS.

### Test 11: Derivatives Notional Exposure

- Scenario: Convert swaps with counterparties, notional amount, effective date, and maturity.
- Expected behavior: Treat notional/exposure carefully, require date basis, and use FIBO DER concepts when available.
- Coverage: FIBO alignment and ambiguity handling.
- Result: PASS.

### Test 12: Legal Entity Identifier

- Scenario: Convert legal entity table with LEI, name, jurisdiction, and registration status.
- Expected behavior: Use `legal_entity_identifier` as a dimension or key, add LEI synonyms, and avoid claiming global uniqueness without evidence.
- Coverage: FIBO alignment example and confidence rules.
- Result: PASS.

### Test 13: Counterparty Risk

- Scenario: Convert exposures by counterparty, product type, rating, and date.
- Expected behavior: Clarify exposure metric, date basis, counterparty identity, and rating source.
- Coverage: Cortex prompt defaults and FIBO relationship terminology.
- Result: PASS.

### Test 14: Market Data Prices

- Scenario: Convert price history with instrument, price date, close, bid, ask, and currency.
- Expected behavior: Define prices as facts, metrics only when meaningful, and clarify price type.
- Coverage: time dimensions, facts vs metrics, ambiguity handling.
- Result: PASS.

### Test 15: Interest Rate Curves

- Scenario: Convert curve points with tenor, rate, curve name, observation date, and currency.
- Expected behavior: Model rates as facts with careful aggregation rules; ask for tenor/date when missing.
- Coverage: non-additive metric and Cortex clarification rules.
- Result: PASS.

### Test 16: Corporate Actions

- Scenario: Convert corporate action events for securities.
- Expected behavior: Align action event terms to FIBO CAE where available; model event dates and event types.
- Coverage: FIBO module hints and event modeling.
- Result: PASS.

### Test 17: Claims Insurance Table

- Scenario: Convert claim transactions with policy, claimant, loss date, paid amount, reserve amount, and status.
- Expected behavior: Define paid/reserve metrics separately, default date rules, and status filters.
- Coverage: metric design checks and prompt defaults.
- Result: PASS.

### Test 18: Policy Premiums

- Scenario: Convert policy premium records by policy, insured, effective period, and coverage.
- Expected behavior: Separate written, earned, and billed premium if columns exist; avoid synonym false equivalence.
- Coverage: metric naming and synonym rules.
- Result: PASS.

### Test 19: Trade Lifecycle

- Scenario: Convert trades with trade date, settlement date, product, counterparty, quantity, and price.
- Expected behavior: Model trade and settlement dates distinctly; clarify default date basis.
- Coverage: time dimension guidance and Cortex ambiguity rules.
- Result: PASS.

### Test 20: Payment Transactions

- Scenario: Convert payments with payer, payee, payment date, amount, channel, and status.
- Expected behavior: Create payment amount/count metrics, active/completed filters, and role-playing party descriptions.
- Coverage: relationship naming and filters.
- Result: PASS.

### Test 21: Many-to-Many Bridge

- Scenario: Convert customers, accounts, and customer-account bridge with ownership percentages.
- Expected behavior: Do not hide many-to-many risk; require allocation semantics before metrics.
- Coverage: bridge guidance and assumptions output.
- Result: PASS.

### Test 22: Role-Playing Date Table

- Scenario: Orders join to date table by order date, ship date, and delivery date.
- Expected behavior: Name each relationship by role and clarify default date.
- Coverage: relationship path naming and verified query examples.
- Result: PASS.

### Test 23: Role-Playing Customer Table

- Scenario: Transactions have buyer, seller, broker, and custodian IDs.
- Expected behavior: Model role-specific relationships and ask for intended perspective when ambiguous.
- Coverage: relationship design and prompt clarification.
- Result: PASS.

### Test 24: Degenerate Dimension

- Scenario: Fact table has order number and invoice number without separate dimension tables.
- Expected behavior: Expose as dimensions when useful for filtering/drill-through, not metrics.
- Coverage: column classification rules.
- Result: PASS.

### Test 25: Sensitive Identifiers

- Scenario: Table includes SSN, tax ID, account number, and legal name.
- Expected behavior: Flag sensitive identifiers; avoid exposing raw PII by default.
- Coverage: FIBO pitfalls, prompt refusal rules.
- Result: PASS.

### Test 26: Missing Primary Keys

- Scenario: Tables lack explicit PK/FK metadata.
- Expected behavior: Infer candidates from names and uniqueness if available, record assumptions, and request confirmation.
- Coverage: intake checklist and relationship validation.
- Result: PASS.

### Test 27: Ambiguous Revenue

- Scenario: Table has gross revenue, net revenue, bookings, and recognized revenue.
- Expected behavior: Define separate metrics and custom instructions for default revenue term.
- Coverage: synonym false-equivalence rules.
- Result: PASS.

### Test 28: Currency Conversion

- Scenario: Amounts exist in transaction currency and reporting currency.
- Expected behavior: Define currency dimensions and metric units; do not mix currencies silently.
- Coverage: metric design and Cortex defaults.
- Result: PASS.

### Test 29: Time Zone Handling

- Scenario: Event timestamps are UTC but users ask local business questions.
- Expected behavior: State timezone assumptions in time dimension descriptions and custom instructions.
- Coverage: prompt default assumptions.
- Result: PASS.

### Test 30: Fiscal Calendar

- Scenario: Date table has fiscal year, fiscal quarter, and fiscal period.
- Expected behavior: Add fiscal dimensions and verified queries that use fiscal groupings.
- Coverage: date dimension and verified query guidance.
- Result: PASS.

### Test 31: Slowly Changing Dimension

- Scenario: Customer segment changes over time with valid-from and valid-to columns.
- Expected behavior: Surface validity assumptions and avoid point-in-time joins unless physical model supports them.
- Coverage: cross-platform dbt SCD notes and assumptions output.
- Result: PASS.

### Test 32: Row-Level Security

- Scenario: Access should be restricted by region or legal entity.
- Expected behavior: Document governance need separately; do not model security as an ordinary analytics filter without confirmation.
- Coverage: AtScale/FIBO platform notes and Snowflake governance caveat.
- Result: PASS.

### Test 33: dbt Semantic Layer Input

- Scenario: Convert dbt semantic models with entities, dimensions, and metrics to Snowflake Semantic Views.
- Expected behavior: Map entities to relationship assumptions, dimensions to dimensions, and metrics to Snowflake metrics.
- Coverage: platform patterns.
- Result: PASS.

### Test 34: Databricks Metric View Input

- Scenario: Convert Databricks metric view YAML to Snowflake Semantic View YAML.
- Expected behavior: Map source, joins, dimensions, measures, and semantic metadata.
- Coverage: platform patterns.
- Result: PASS.

### Test 35: LookML Input

- Scenario: Convert Looker model/explore/view files.
- Expected behavior: Map Explores and joins to relationships, views to logical tables, fields to dimensions/metrics.
- Coverage: platform patterns.
- Result: PASS.

### Test 36: Power BI Model Input

- Scenario: Convert Power BI tables, relationships, DAX measures, and hierarchies.
- Expected behavior: Translate DAX measures to SQL metric intent, not literal syntax; preserve relationship and RLS caveats.
- Coverage: platform patterns.
- Result: PASS.

### Test 37: Cube Model Input

- Scenario: Convert Cube cubes, joins, measures, dimensions, and access policies.
- Expected behavior: Map cubes to logical tables and warn about join fanout and access policy translation.
- Coverage: platform patterns.
- Result: PASS.

### Test 38: AtScale SML Input

- Scenario: Convert AtScale SML model with datasets, dimensions, metrics, and relationships.
- Expected behavior: Map datasets/dimensions to logical tables and metrics/calculations to Snowflake metrics.
- Coverage: platform patterns and attached AtScale reference.
- Result: PASS.

### Test 39: FIBO Class Explanation Before Modeling

- Scenario: User asks to model bonds but first wants the domain terms grounded.
- Expected behavior: Use FIBO search workflow and cite RDF paths before model naming.
- Coverage: FIBO ontology alignment.
- Result: PASS.

### Test 40: FIBO Ambiguous Local Name

- Scenario: User asks to map `Security` without module context.
- Expected behavior: Disambiguate by IRI/prefix/file path and definition.
- Coverage: FIBO skill rules included by reference.
- Result: PASS.

### Test 41: FIBO Object Property as Join Hint

- Scenario: Ontology says an instrument has issuer, but warehouse join columns are absent.
- Expected behavior: Use ontology as semantic description only; do not create unsupported Snowflake relationship.
- Coverage: FIBO mapping rules.
- Result: PASS.

### Test 42: FIBO Datatype Property as Field

- Scenario: Column resembles maturity date or coupon rate.
- Expected behavior: Map datatype property evidence to time dimension or fact, with confidence and file path.
- Coverage: FIBO mapping rules.
- Result: PASS.

### Test 43: Verified Query Generation

- Scenario: User asks for prompts to help answer any supported question.
- Expected behavior: Generate representative verified queries covering top-N, trend, filter, derived metric, and ambiguity cases.
- Coverage: Cortex prompt and verified query sections.
- Result: PASS.

### Test 44: Unsupported User Question

- Scenario: User asks for external benchmark data not present in the model.
- Expected behavior: Custom instructions tell Cortex Analyst to say unavailable and explain missing data.
- Coverage: refusal rules.
- Result: PASS.

### Test 45: Natural Language Prompt Package

- Scenario: User asks for the best user prompt to query the data model.
- Expected behavior: Produce business context, default assumptions, metric rules, ambiguity handling, and example questions.
- Coverage: `cortex-analyst-prompting.md`.
- Result: PASS.

### Test 46: YAML Validation Command

- Scenario: User asks how to validate generated YAML.
- Expected behavior: Provide `SYSTEM$CREATE_SEMANTIC_VIEW_FROM_YAML(..., TRUE)` verify-only command.
- Coverage: Snowflake validation guidance.
- Result: PASS.

### Test 47: Do Not Execute DDL

- Scenario: User requests generation only.
- Expected behavior: Do not execute create/replace DDL unless explicitly requested.
- Coverage: validation and workflow rules.
- Result: PASS.

### Test 48: Partial Schema Input

- Scenario: User provides table names and a few columns only.
- Expected behavior: Use modeling intake checklist and proceed with clearly labeled assumptions.
- Coverage: intake template and assumptions output.
- Result: PASS.

### Test 49: Full Deliverable Request

- Scenario: User requests complete Snowflake semantic model package.
- Expected behavior: Produce YAML, ontology alignment, Cortex instructions, verified queries, assumptions, and validation SQL.
- Coverage: required output section.
- Result: PASS.

### Test 50: Skill Discoverability

- Scenario: User asks for Snowflake schematic/semantic model from tables and ontology.
- Expected behavior: Skill frontmatter triggers on Snowflake Semantic View, FIBO, ontology-aligned financial data, and Cortex Analyst prompt package.
- Coverage: `SKILL.md` frontmatter and `agents/openai.yaml`.
- Result: PASS.

## Findings

- The skill covers the main conversion surfaces: single table, star schema, snowflake schema, multi-role relationships, non-additive metrics, external semantic-layer inputs, and FIBO ontology alignment.
- The strongest scenarios are financial-domain cases where FIBO clarifies terms, but the skill correctly prevents ontology-only relationships from becoming physical joins.
- The highest-risk scenarios are many-to-many bridges, row-level security, DAX translation, SCD Type II joins, and mixed-currency metrics. The skill now directs the agent to surface assumptions instead of hiding them.
- The prompt-generation path is strong enough for practical use: it separates SQL generation rules from question-categorization rules and includes refusal/clarification behavior.

