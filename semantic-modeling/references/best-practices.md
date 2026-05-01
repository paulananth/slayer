# Best Practices

Use these practices when converting tables and ontology concepts into Snowflake Semantic Views.

## Start With Business Grain

Define the grain before writing metrics:

- One row per event, order, order line, account snapshot, position, security, party, loan, or claim.
- For snapshot tables, name the snapshot date and treat balances carefully.
- If grain is uncertain, write the assumption and avoid high-confidence metric claims.

Bad:

```text
This table has amount, so create total amount.
```

Good:

```text
The table appears to be one row per loan per snapshot_date. outstanding_principal is a point-in-time balance and should not be summed across snapshot_date.
```

## Separate Warehouse Truth From Ontology Meaning

Use FIBO to improve semantic precision, not to invent data.

- FIBO can justify a name, description, synonym, or relationship meaning.
- FIBO cannot prove a physical foreign key exists.
- FIBO restrictions are not database constraints unless the warehouse enforces them.
- Cite RDF files and confidence when using ontology mappings.

## Prefer Semantic Metrics Over Raw Calculations

In custom instructions, tell Cortex Analyst to use modeled metrics first.

Good:

```text
Use total_net_revenue for revenue questions unless the user explicitly asks for gross revenue, bookings, or recognized revenue.
```

Bad:

```text
Calculate revenue from whatever amount field seems relevant.
```

## Do Not Hide Ambiguity

Ask for clarification when users could mean different things:

- trade date vs settlement date
- issuer vs obligor vs counterparty
- gross revenue vs net revenue vs bookings
- coupon rate vs yield
- market value vs book value
- current balance vs average balance

Model ambiguity in `AI_QUESTION_CATEGORIZATION`, not only in documentation.

## Use Synonyms Conservatively

Synonyms help Cortex Analyst, but false synonyms produce wrong answers.

Good synonyms:

- `legal_entity_identifier`: `LEI`, `legal entity id`
- `net_revenue`: `net sales`, if the business confirms equivalence
- `security`: `instrument`, only if the modeled domain uses them interchangeably

Bad synonyms:

- `issuer`: `counterparty`
- `coupon_rate`: `yield`
- `booking_amount`: `recognized_revenue`
- `balance`: `exposure`

## Make Time Defaults Explicit

Every prompt package should state:

- default date dimension
- timezone
- fiscal vs calendar period
- whether incomplete periods are included
- how snapshot metrics choose a date

For multi-date tables, verified queries should demonstrate the difference.

## Treat Non-Additive Metrics As High Risk

Use special care for:

- balances
- inventory
- exposures
- rates
- ratios
- percentages
- distinct counts
- market prices

Prefer helper metrics for numerator and denominator, then derived metrics for ratios.

## Write Verified Queries As Teaching Examples

Verified queries should cover the most important user intents:

- top-N
- time trend
- metric by dimension
- common filter
- derived metric
- ambiguity resolution

Avoid dozens of near-duplicate examples. A few high-quality verified queries are better than many shallow ones.

## Keep Cortex Instructions Operational

Split instructions by purpose:

- `AI_SQL_GENERATION`: how to generate SQL and choose metrics/fields.
- `AI_QUESTION_CATEGORIZATION`: when to clarify, reject, or classify unsupported questions.

Use short bullets. Avoid narrative background that does not change behavior.

## Preserve Security Boundaries

Do not expose raw sensitive fields by default:

- SSN, tax IDs, account numbers, personal names, addresses, emails
- legal identifiers that are sensitive in context
- row-level customer or counterparty data when the model is intended for aggregate analytics

Use `private_access` for helper facts/metrics and document Snowflake governance needs separately.

## Validate Before Create

Always provide verify-only SQL:

```sql
SELECT SYSTEM$CREATE_SEMANTIC_VIEW_FROM_YAML(
  '<database>.<schema>',
  $$<semantic view YAML>$$,
  TRUE
);
```

Do not execute create/replace DDL unless the user explicitly asks.

