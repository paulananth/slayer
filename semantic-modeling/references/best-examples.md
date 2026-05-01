# Best Examples

These examples show the strongest ways to use the skill. They are intentionally compact and focus on inputs, expected outputs, and modeling judgment.

## Example 1: Financial Instrument Holdings With FIBO Alignment

User prompt:

```text
Use $semantic-modeling to convert these Snowflake tables into a semantic view:
- MART.HOLDINGS.POSITION(position_id, security_id, account_id, as_of_date, quantity, market_value_usd, book_value_usd)
- MART.HOLDINGS.SECURITY(security_id, isin, cusip, issuer_lei, security_type, coupon_rate, maturity_date, currency)
- MART.REF.LEGAL_ENTITY(lei, legal_name, jurisdiction, entity_status)
Use FIBO concepts for security, issuer, legal entity identifier, coupon, maturity, and market value. Also create the Cortex Analyst custom instructions.
```

Why it is strong:

- It provides physical tables and columns.
- It names the financial concepts that need FIBO grounding.
- It asks for both Snowflake YAML and the prompt package.

Expected output:

- Logical tables: `positions`, `securities`, `legal_entities`.
- Relationships: `positions_to_securities`, `securities_to_issuers`.
- Time dimension: `as_of_date`.
- Facts: `quantity`, `market_value_usd`, `book_value_usd`.
- Metrics: `total_market_value_usd`, `total_book_value_usd`, `position_count`.
- Ontology alignment for security, issuer/legal entity, coupon rate, maturity date, and identifiers.
- `AI_SQL_GENERATION` rule that market value defaults to USD and position metrics use `as_of_date`.
- `AI_QUESTION_CATEGORIZATION` rule that asks for date when the user asks for current holdings without one.

## Example 2: Loan Portfolio Balance Model

User prompt:

```text
Use $semantic-modeling to build a Snowflake semantic view for a loan portfolio.
Tables:
- CORE.LOAN.LOAN_ACCOUNT(loan_id, borrower_id, product_code, origination_date, maturity_date, interest_rate, original_principal)
- CORE.LOAN.LOAN_BALANCE(loan_id, snapshot_date, outstanding_principal, accrued_interest, delinquency_status)
- CORE.PARTY.BORROWER(borrower_id, borrower_name, borrower_type, jurisdiction)
Ground the domain vocabulary in FIBO where possible and make the prompt robust for balance questions.
```

Why it is strong:

- It has a snapshot table, so non-additivity is testable.
- It names the desired robustness for natural-language balance questions.

Expected output:

- `outstanding_principal` modeled as non-additive across `snapshot_date`.
- Custom instructions that require a snapshot date or use an explicit default.
- FIBO alignment for loan, borrower, maturity, interest rate, and principal.
- Verified queries for period-end outstanding principal and delinquency status.

## Example 3: Ambiguous Revenue Model

User prompt:

```text
Use $semantic-modeling to convert SALES.ORDER_LINE(order_line_id, order_id, customer_id, order_date, ship_date, gross_amount, discount_amount, net_amount, booking_amount, recognized_revenue, status, channel) into Snowflake Semantic View YAML. Include the best Cortex Analyst prompt so users don't confuse bookings, gross revenue, net revenue, and recognized revenue.
```

Why it is strong:

- It calls out the central ambiguity.
- It forces metric separation and prompt rules.

Expected output:

- Separate metrics for gross revenue, net revenue, bookings, and recognized revenue.
- Synonyms that do not make false equivalents.
- Default rule: if the business chooses `net_revenue` as default, state it explicitly.
- Categorization rule: ask for clarification when a user asks for "sales" if no default is supplied.

## Example 4: Multi-Role Date and Party Model

User prompt:

```text
Use $semantic-modeling to model TRADE(trade_id, buyer_id, seller_id, broker_id, instrument_id, trade_date, settlement_date, quantity, price, notional_amount) with PARTY(party_id, legal_name, lei) and INSTRUMENT(instrument_id, instrument_type, issuer_id, maturity_date). Use FIBO terms and create verified questions for trade date versus settlement date.
```

Why it is strong:

- It tests role-playing relationships and date ambiguity.
- It uses FIBO for financial parties and instruments.

Expected output:

- Relationships named by role: `trades_to_buyers`, `trades_to_sellers`, `trades_to_brokers`, `instruments_to_issuers`.
- Time dimensions for `trade_date` and `settlement_date`.
- Prompt rule: ask which date basis to use unless the question explicitly says trade or settlement.

## Example 5: Existing Semantic Layer Migration

User prompt:

```text
Use $semantic-modeling to convert this LookML/AtScale/dbt semantic model into a Snowflake Semantic View. Preserve the business metric definitions, map source dimensions and joins, and produce Cortex Analyst custom instructions plus verified queries.
```

Why it is strong:

- It is tool-neutral but specifies the target.
- It asks to preserve semantic intent rather than syntax.

Expected output:

- Source concepts mapped through `platform-patterns.md`.
- Derived metrics moved to Snowflake view-level metrics when appropriate.
- Legacy join types removed when converting to Snowflake Semantic Views.
- Custom instructions separated from YAML.

## Example 6: Complex Fixture for Regression Testing

Local artifacts:

- `examples/complex-financial-model/schema.sql`
- `examples/complex-financial-model/semantic-view.yaml`
- `examples/complex-financial-model/cortex-instructions.sql`
- `examples/complex-financial-model/ontology-alignment.md`
- `tests/test_semantic_layer_artifacts.py`

What it tests:

- Snowflake tables plus analytic views for instruments, positions, trades, legal entities, market prices, FX rates, and risk exposures.
- Role-playing party relationships: issuer, obligor, custodian, buyer, seller, broker, and counterparty.
- Multiple date bases: position as-of date, exposure date, trade date, settlement date, issue date, and maturity date.
- Non-additive metrics for point-in-time market value and exposure.
- FIBO-style ontology alignment notes with confidence and boundary rules.
- Cortex Analyst `AI_SQL_GENERATION` and `AI_QUESTION_CATEGORIZATION` guidance.

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -t . -q
```
