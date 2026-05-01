# FIBO Ontology Alignment for Snowflake Semantic Views

Use this reference when financial-domain tables should be converted into Snowflake Semantic Views with FIBO-grounded business meaning.

Primary local skill:

- FIBO skill: `/mnt/c/Users/paula/.codex/skills/SKILL.md`

Primary FIBO repository evidence:

- Treat the checked-out FIBO repository as source of truth.
- Verify all classes, properties, restrictions, definitions, and imports in `.rdf` files.
- Resolve ontology IRIs through `catalog-v001.xml`.

## When to Use FIBO

Use FIBO alignment when table or column names mention:

- legal entities, parties, organizations, identifiers, LEI
- financial instruments, securities, bonds, equities, funds
- loans, credit agreements, debt, mortgages
- derivatives, swaps, options, futures, forwards
- market data, prices, rates, indices, benchmarks
- corporate actions, issuance, listings, baskets
- accounts, positions, holdings, exposures, transactions
- financial contracts, obligations, terms, maturity, coupon, notional

Do not force FIBO alignment for generic operational fields such as load timestamps, ETL batch IDs, raw source file names, or technical audit columns.

## FIBO Search Workflow

From the FIBO repository root:

```bash
ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
rg -n 'rdf:about="[^"]*(;|#)<LocalName>"' -g '*.rdf' "$ROOT"
rg -n '<(rdfs:label|skos:definition)[^>]*>.*<business phrase>' -g '*.rdf' "$ROOT"
rg -n '(^|[;#/])<LocalName>("|<|$)' -g '*.rdf' "$ROOT"
```

Resolve imports and module location:

```bash
rg -n 'owl:imports' <module-file.rdf>
rg -n '<module-or-IRI-fragment>' catalog-v001.xml
```

When completeness matters, search for every same-IRI block across the repository. FIBO can add axioms about an entity outside the file that originally defines it.

## Mapping Rules

Map FIBO evidence to Snowflake Semantic View elements:

| FIBO construct | Snowflake semantic view use |
| --- | --- |
| `owl:Class` | logical table, dimension concept, or business entity description |
| `owl:ObjectProperty` | relationship meaning, join-path name, or semantic description |
| `owl:DatatypeProperty` | dimension, time dimension, fact, or metric source field |
| `skos:definition` | authoritative field/table/metric description |
| `rdfs:label` | display wording and synonyms |
| `skos:note` / `skos:example` | custom instructions and clarification text |
| `owl:Restriction` | modeling constraint or assumption to verify against data |
| named individual | enum value, sample value, or clarification vocabulary |

Never create a physical Snowflake relationship from ontology meaning alone. A semantic relationship still needs columns that support the join.

## Domain Module Hints

Use these FIBO areas as starting points:

- `FND/`: foundations, contracts, parties, dates, accounting, relations, products and services
- `BE/`: legal entities, government entities, trusts, ownership and control
- `FBC/`: financial instruments, products, services, markets, debt base classes
- `SEC/`: securities, bonds, equities, funds, listings, restrictions, baskets, issuance
- `DER/`: swaps, options, futures, forwards, credit derivatives
- `LOAN/`: loans and real-estate loans
- `CAE/`: corporate actions and events
- `IND/`: indicators, interest rates, foreign exchange, market indices
- `MD/`: market data for securities, derivatives, debt, and funds
- `BP/`: business process and securities issuance
- `ACTUS/`: ACTUS contract term mappings and examples

## Output: Ontology Alignment Section

Include an ontology alignment section whenever FIBO was used:

```markdown
## Ontology Alignment

| Model element | FIBO term | IRI or prefix | Evidence | Mapping confidence |
| --- | --- | --- | --- | --- |
| instrument.security_id | Security identifier | fibo-fbc-fi-fi:Security | FBC/.../FinancialInstruments.rdf | High |
```

For each mapped concept, include:

- local model element
- FIBO class/property/individual
- file path used as evidence
- definition summary
- confidence: High, Medium, or Low
- unresolved ambiguity

Confidence guidance:

- High: exact label/name and definition match the table/column business meaning.
- Medium: label matches but definition or restrictions need stakeholder confirmation.
- Low: only substring, abbreviation, or inferred relationship matches.

## Snowflake YAML Guidance

Use FIBO to improve:

- logical table descriptions
- field descriptions
- metric definitions
- synonyms and abbreviations
- relationship names and descriptions
- verified query wording
- Cortex Analyst ambiguity rules

Example:

```yaml
dimensions:
  - name: legal_entity_identifier
    synonyms: ["LEI", "entity identifier", "legal entity id"]
    description: "Identifier for a legal entity, aligned to the FIBO legal entity identifier concept. Verify issuing authority and format constraints before treating as globally unique."
    expr: lei
    data_type: VARCHAR
    unique: true
```

## Cortex Analyst Prompt Guidance

Add ontology-grounded instructions:

```text
Ontology grounding:
- Use the modeled FIBO-aligned definitions for financial terms such as security, issuer, obligor, notional amount, coupon, maturity, and legal entity.
- If a user term has multiple FIBO-aligned meanings, ask for clarification rather than guessing.
- Do not infer regulatory classifications, instrument type, or contract terms unless represented by modeled fields or verified queries.
```

Include user-facing prompts that tell analysts what the model can answer:

```text
Ask questions about holdings, securities, issuers, counterparties, balances, rates, maturity dates, and exposure metrics that are represented in this semantic view. For terms with multiple financial meanings, specify the instrument type, date basis, and metric definition.
```

## Common Pitfalls

- Do not replace database truth with ontology assumptions.
- Do not map local names globally without checking IRI, module, and definition.
- Do not collapse multiple inheritance into a single parent.
- Do not treat a FIBO restriction as a database constraint unless the data enforces it.
- Do not expose raw sensitive identifiers simply because FIBO defines them.
- Do not add synonyms that make distinct financial terms equivalent.

