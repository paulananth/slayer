# Relationship Inference

Relationship inference is the highest-risk part of semantic model generation. Use `tools/relationship_inferencer.py` when relationships must be inferred across warehouse tables or imported semantic models.

## Principles

- Prefer explicit active relationships from source metadata.
- Use physical warehouse columns or model columns only; ontology meaning is not enough.
- Put the foreign-key side in `left_table` and the unique/reference side in `right_table`.
- Treat inactive relationships, many-to-many relationships, and tied candidates as manual-review items.
- Preserve role-playing names, such as buyer, seller, broker, issuer, obligor, custodian, and counterparty.

## Evidence Used

The routine scores candidates from:

- explicit source-model relationships, such as Power BI relationships
- column-name matches, such as `customer_id` to `customer_id`
- key suffixes, such as `_id`, `_key`, `_code`, and `_lei`
- referenced-column uniqueness
- fact-like source table shape and dimension-like target table shape
- role-playing party/entity patterns
- table-name prefixes such as `fact_`, `dim_`, `vw_`, and `stg_`

## Safety Behavior

- Explicit active relationships have highest confidence.
- Many-to-many source relationships are skipped until bridge/allocation semantics are modeled.
- Inactive source relationships are skipped because they usually require explicit DAX or query-time activation semantics.
- Ambiguous inferred candidates are skipped when multiple targets have near-equal confidence.
- Unique-to-unique dimension-style relationships are skipped unless explicit metadata supports them.

## Outputs

The routine returns:

- relationship candidates with name, left table, right table, columns, confidence, source, and reason
- warnings for inactive, many-to-many, missing-table, missing-column, and ambiguous candidates

Converters should include warnings in conversion notes or assumptions, not hide them.
