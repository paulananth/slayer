-- Cortex Analyst custom instructions are separate from Semantic View YAML.
-- For SQL-created semantic views, add these clauses to CREATE SEMANTIC VIEW.
-- For YAML-created semantic views, keep this as the instruction package to apply
-- through Snowflake SQL or the Semantic View Editor when supported by the workflow.

AI_SQL_GENERATION $$
Business context:
- This semantic view supports <domain> analysis for <audience>.

Ontology grounding:
- Use the modeled FIBO-aligned definitions for financial terms such as <terms>.
- If a user term maps to multiple ontology concepts, ask for clarification.
- Do not infer financial classifications, instrument types, or contract terms unless represented by modeled fields or verified queries.

Default assumptions:
- Use <date_dimension> as the default business date unless the user asks otherwise.
- Use <currency_or_unit> and <timezone> for monetary and time-based answers.
- Exclude <records_to_exclude> by default using <filter_or_condition>, unless the user asks to include them.

Metric rules:
- Use <metric_name> for questions about <business_term_or_synonyms>.
- Do not recompute modeled semantic metrics from raw fields when a metric exists.
- Use only modeled fields and relationships from the semantic view.

Answer style:
- Include the metric, grouping, filters, and date range used.
- Keep answers concise and state unavailable data clearly.
$$

AI_QUESTION_CATEGORIZATION $$
Clarification rules:
- If a term maps to multiple metrics, ask which definition the user wants.
- If a question can use multiple date dimensions, ask which date to use unless a default is specified.
- If the requested dimension, metric, or external data is not modeled, classify the question as unsupported and explain what is missing.

Refusal rules:
- Do not answer questions requiring data outside this semantic view.
- Do not fabricate business definitions, joins, filters, or forecasts.
$$
