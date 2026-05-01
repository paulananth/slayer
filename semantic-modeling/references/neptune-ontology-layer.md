# AWS Neptune Ontology Layer

Use this reference when AWS Neptune is part of the semantic-modeling architecture.

Authoritative AWS documentation:

- Amazon Neptune overview: https://docs.aws.amazon.com/neptune/latest/userguide/intro.html
- SPARQL access in Neptune: https://docs.aws.amazon.com/neptune/latest/userguide/access-graph-sparql.html
- Neptune Analytics overview: https://docs.aws.amazon.com/neptune-analytics/latest/userguide/what-is-neptune-analytics.html

## Role in the Architecture

Use Neptune as the ontology and GraphRAG context layer above and beside the Snowflake semantic model.

Neptune owns:

- FIBO RDF/OWL and internal financial vocabulary.
- Definitions, labels, synonyms, class hierarchy, and object/datatype property meaning.
- Term disambiguation for financial concepts such as issuer, obligor, counterparty, LEI, coupon, maturity, exposure, and security.
- Optional graph retrieval context for LLM/Cortex prompts.

Snowflake owns:

- Physical analytical tables/views.
- Snowflake Semantic Views.
- Metrics, facts, dimensions, filters, relationships, verified queries, and SQL execution.
- Metric answers such as AUM, exposure, balances, market value, trade notional, counts, and ratios.

## Query Responsibilities

Use Neptune/SPARQL for questions like:

- What does this financial term mean?
- Which FIBO concept best maps to this table or column?
- What are related concepts, synonyms, subclasses, or parent classes?
- Is issuer the same as counterparty, obligor, or custodian?

Use Snowflake SQL for questions like:

- What is total AUM by account group?
- What is exposure by counterparty?
- What is market value by issuer?
- What is trade notional by settlement status?

## GraphRAG Routing

Routing logic:

1. If the question needs meaning, synonyms, hierarchy, or disambiguation, retrieve Neptune context first.
2. Map the resolved concept to the semantic model.
3. If the question needs a metric, generate Snowflake SQL only from modeled semantic fields.
4. If the semantic model lacks a metric, date basis, relationship path, grouping type, or allocation rule, ask for clarification or return a model-gap response.

Never use GraphRAG context as proof of data availability.

## SPARQL Term Lookup Examples

Find terms by label or definition:

```sparql
SELECT ?term ?label ?definition
WHERE {
  ?term rdfs:label ?label .
  OPTIONAL { ?term skos:definition ?definition . }
  FILTER(CONTAINS(LCASE(STR(?label)), "issuer"))
}
LIMIT 25
```

Find hierarchy:

```sparql
SELECT ?parent ?parentLabel
WHERE {
  ?term rdfs:label "security"@en .
  ?term rdfs:subClassOf+ ?parent .
  OPTIONAL { ?parent rdfs:label ?parentLabel . }
}
LIMIT 50
```

Find properties related to a concept:

```sparql
SELECT ?property ?label ?definition
WHERE {
  ?property a rdf:Property .
  OPTIONAL { ?property rdfs:label ?label . }
  OPTIONAL { ?property skos:definition ?definition . }
  FILTER(CONTAINS(LCASE(STR(?label)), "maturity"))
}
LIMIT 25
```

## Semantic Model Guardrails

Follow these rules strictly:

- Neptune can enrich semantic model descriptions, synonyms, and clarification prompts.
- Neptune can identify candidate FIBO/internal ontology mappings.
- Neptune cannot create a Snowflake join without warehouse keys and semantic-model relationships.
- Neptune cannot create a metric that is absent from the Snowflake semantic model.
- Neptune cannot answer numeric metric questions unless the required values are intentionally materialized back into Snowflake.
- Ontology object properties describe meaning, not physical cardinality.
- GraphRAG retrieved context must be cited or summarized separately from metric outputs.

## Output Pattern

When using Neptune context, include:

```text
Ontology context:
- Resolved term:
- Neptune/SPARQL evidence:
- Related concepts:
- Ambiguities:

Semantic mapping:
- Metric:
- Dimensions:
- Filters:
- Date basis:
- Relationship path:

Snowflake SQL:
- Only if the semantic model supports the request.
```

## Optional Neptune Analytics

Use Neptune Analytics later for graph algorithms and vector search when the use case requires:

- centrality or influence analysis
- community detection
- path analysis
- concentration or connected-risk exploration
- graph-derived features materialized back into Snowflake

Do not require Neptune Analytics for the first ontology-layer implementation.

