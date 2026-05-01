# Cortex Analyst Prompting and Custom Instructions

Goal: help Cortex Analyst answer natural-language questions using only the semantic view definitions, verified queries, and available data.

## Principles

Write instructions that are compact, explicit, and operational. Avoid broad prose.

Good instructions:

- Define business terms.
- Use ontology-grounded definitions when the model is aligned to FIBO or another domain ontology.
- Set defaults for date ranges, currency, timezone, and filters.
- Explain which metrics to prefer.
- Explain how to handle ambiguity.
- Tell the model when to ask a clarifying question.
- Tell the model not to invent unavailable data or unsupported joins.

Weak instructions:

- "Answer all questions accurately."
- "Use common sense."
- Long background narratives.
- Policy hidden in examples only.

## Recommended Instruction Structure

Use this structure:

```text
Business context:
- This semantic view supports <domain> analysis for <audience>.

Ontology grounding:
- Use the modeled FIBO-aligned definitions for <financial terms>.
- If a user term maps to multiple ontology concepts, ask for clarification.
- Do not infer financial classifications or contract terms unless represented by modeled fields.

Default assumptions:
- Use <date dimension> as the default business date unless the user asks otherwise.
- Use <currency/unit/timezone> for all monetary/time answers.
- Exclude <records> by default using <filter/condition>, unless the user asks to include them.

Metric rules:
- Use <metric_name> for questions about <business term/synonyms>.
- Use <metric_name> for distinct customer/account/user counts.
- Do not recompute <metric_name> from raw fields when a semantic metric exists.

Ambiguity handling:
- If the user asks for <ambiguous term>, clarify whether they mean <A> or <B>.
- If the requested data is not modeled, say it is not available in this semantic view.

Answer style:
- Return concise answers with the metric, grouping, filters, and date range used.
- When SQL is returned, use semantic view names and modeled fields only.
```

## Synonyms

Add synonyms for:

- Common business terms: revenue, sales, bookings, ARR, churn, claims, premium.
- Abbreviations: AOV, GMV, CAC, LTV, MRR.
- FIBO labels and common financial aliases when the definitions truly match the modeled field.
- Source-system labels users know.
- Singular/plural forms.
- Domain-specific aliases.

Do not add synonyms that create false equivalence. If "revenue" and "bookings" differ, define separate metrics and state the difference.

For financial terms, do not make near-neighbors equivalent. Examples: issuer vs obligor, price vs value, balance vs exposure, coupon rate vs yield, security vs financial instrument, booking vs trade.

## Descriptions

Descriptions should answer:

- What business concept does this field represent?
- What is included and excluded?
- What is the unit?
- What date or grain governs it?
- When should a user choose this field instead of a nearby field?

Examples:

```yaml
description: "Net revenue in USD after item discounts and before refunds, grouped by order date."
```

```yaml
description: "Customer segment assigned by the CRM at the time the customer record was last updated."
```

## Verified Queries

Each semantic view should include verified queries for the most likely tasks:

- "What is total revenue by month?"
- "Who are the top 10 customers by revenue?"
- "What is average order value by channel?"
- "How many active customers did we have last quarter?"
- "What is gross margin rate by product category?"

Prefer SQL that demonstrates:

- The default time dimension.
- The preferred metric.
- A common filter.
- A join path through relationships.
- A derived metric.

## Refusal and Clarification Rules

Tell Cortex Analyst to clarify when:

- The metric term has multiple modeled meanings.
- A financial term maps to multiple FIBO concepts or instrument types.
- The user asks for a time range but no default exists.
- The requested dimension is unavailable.
- A requested comparison needs external data.
- The question implies row-level PII output and the view is intended for aggregate analytics.

Tell Cortex Analyst to refuse or explain unavailability when:

- The answer requires data outside the semantic view.
- The user requests a calculation that would violate the metric definition.
- The user asks for unsupported causal claims or forecasts.
- The user asks for ontology-derived facts that were not materialized or verified in the warehouse data.

## SQL Template

Use `assets/templates/custom-instructions.sql` as a starting point. Keep instructions short enough to be maintainable.

Current Snowflake SQL-created semantic views support:

- `AI_SQL_GENERATION '<instructions>'` for SQL generation rules.
- `AI_QUESTION_CATEGORIZATION '<instructions>'` for classification, clarification, and rejection rules.

These instructions are not fields in the Semantic View YAML specification.
