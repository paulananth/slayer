# Semantic Modeling Skill

This repository contains a Codex skill named `semantic-modeling` plus helper tools for generating Snowflake Semantic View artifacts.

Use it to convert warehouse schemas, Power BI PBIX semantic models, existing semantic-layer definitions, or financial-domain metadata into:

- Snowflake Semantic View YAML
- Cortex Analyst custom instructions
- verified queries
- relationship inference notes
- ontology/FIBO alignment notes
- verify-only Snowflake validation SQL

## Add The Skill To Codex

Codex skills live under `$CODEX_HOME/skills`. If `CODEX_HOME` is not set, use `~/.codex`.

From the repository root:

```bash
export CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
mkdir -p "$CODEX_HOME/skills"
cp -R semantic-modeling "$CODEX_HOME/skills/semantic-modeling"
```

For local development, a symlink is easier because edits in this repo are immediately visible:

```bash
export CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
mkdir -p "$CODEX_HOME/skills"
ln -sfn "$(pwd)/semantic-modeling" "$CODEX_HOME/skills/semantic-modeling"
```

Restart Codex after adding or updating the skill so it reloads `semantic-modeling/SKILL.md`.

## Verify The Skill Files

The skill entry point is:

```text
semantic-modeling/SKILL.md
```

The skill should include these supporting folders:

```text
semantic-modeling/assets/templates/
semantic-modeling/references/
```

Run the tests:

```bash
python3 -m unittest discover -s tests -t . -q
```

## Install Tool Dependencies

The Python tools use the packages in `requirements.txt`.

```bash
python3 -m pip install -r requirements.txt
```

Important dependencies:

- `pyyaml`: writes Snowflake Semantic View YAML
- `snowconn`: connects to Snowflake for schema introspection
- `pbixray`: reads Power BI `.pbix` and PowerPivot `.xlsx` model metadata

## Use The Skill In Codex

Example prompt:

```text
Use $semantic-modeling to convert these Snowflake tables into a Snowflake Semantic View.

Tables:
- MART_SALES.FACT_SALES(...)
- MART_SALES.DIM_CUSTOMER(...)
- MART_SALES.DIM_DATE(...)

Create the YAML, Cortex Analyst instructions, verified queries, assumptions, and verify-only validation SQL.
```

For financial concepts, ask for FIBO grounding:

```text
Use $semantic-modeling to model these holdings, securities, issuers, and legal entities.
Use FIBO-style concepts for issuer, legal entity identifier, instrument, coupon, maturity, and market value.
```

## Generate From Snowflake Metadata

Use `tools.semantic_brainstormer` when Snowflake table metadata is available.

```bash
python3 -m tools.semantic_brainstormer \
  --database ANALYTICS \
  --schemas MART_FINANCE,MART_RISK \
  --connection myconn \
  --view-name financial_risk_semantic_view \
  --output-dir generated/
```

This writes:

```text
generated/<view_name>.yaml
generated/<view_name>_create.sql
```

The generated SQL validates first with `SYSTEM$CREATE_SEMANTIC_VIEW_FROM_YAML(..., TRUE)`.

## Convert A Power BI PBIX Model

Use `tools.pbixray_semantic_converter` when you have a `.pbix` or PowerPivot `.xlsx` file.

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

This writes:

```text
generated/pbix_sales/sales_semantic_view.yaml
generated/pbix_sales/sales_semantic_view_create.sql
generated/pbix_sales/sales_semantic_view_conversion_notes.md
```

Power BI model tables are abstract. Snowflake Semantic Views require actual Snowflake tables or views, so use `--table-map` to map Power BI model table names to physical Snowflake tables or compatibility views.

## Relationship Inference

Relationship inference is handled by:

```text
tools/relationship_inferencer.py
semantic-modeling/references/relationship-inference.md
```

The routine:

- prefers explicit active relationships from source models
- infers candidates from key names, uniqueness, table shape, and role-playing party patterns
- skips inactive relationships
- skips many-to-many relationships until bridge/allocation semantics are modeled
- skips ambiguous ties and reports them for manual review

## Repository Guide

Key files:

```text
semantic-modeling/SKILL.md
semantic-modeling/references/
semantic-modeling/assets/templates/
tools/semantic_brainstormer.py
tools/pbixray_semantic_converter.py
tools/relationship_inferencer.py
tests/
spec.md
usecases.md
```

## Development Workflow

After changing the skill, tools, or docs:

```bash
python3 -m unittest discover -s tests -t . -q
git status -sb
```

Commit intentionally:

```bash
git add <changed-files>
git commit -m "Describe the change"
git push origin main
```
