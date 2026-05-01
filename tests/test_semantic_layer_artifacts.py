import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples" / "complex-financial-model"
SCHEMA_SQL = EXAMPLE / "schema.sql"
SEMANTIC_YAML = EXAMPLE / "semantic-view.yaml"
CORTEX_SQL = EXAMPLE / "cortex-instructions.sql"
ONTOLOGY = EXAMPLE / "ontology-alignment.md"
GUARDRAILS = ROOT / "semantic-modeling" / "references" / "sql-generation-guardrails.md"
SQL_PROMPT_TEMPLATE = ROOT / "semantic-modeling" / "assets" / "templates" / "semantic-sql-request.md"
NEPTUNE_REF = ROOT / "semantic-modeling" / "references" / "neptune-ontology-layer.md"
NEPTUNE_ARCH = ROOT / "docs" / "neptune-semantic-model-architecture.md"
NEPTUNE_ROUTING = EXAMPLE / "neptune-graphrag-routing.md"
SPARQL_LOOKUPS = EXAMPLE / "sparql-term-lookups.sparql"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def logical_tables(yaml_text: str) -> set[str]:
    return set(re.findall(r"^  - name: ([a-z0-9_]+)$", yaml_text, flags=re.MULTILINE))


def relationship_table_refs(yaml_text: str) -> list[str]:
    return re.findall(r"^\s+(?:left_table|right_table): ([a-z0-9_]+)$", yaml_text, flags=re.MULTILINE)


class SemanticLayerArtifactTests(unittest.TestCase):
    def test_complex_schema_contains_multiple_tables_and_views(self):
        sql = read(SCHEMA_SQL)
        tables = re.findall(r"CREATE OR REPLACE TABLE MART_FINANCE\.([A-Z0-9_]+)", sql)
        views = re.findall(r"CREATE OR REPLACE VIEW MART_FINANCE\.([A-Z0-9_]+)", sql)

        self.assertGreaterEqual(len(tables), 7)
        self.assertGreaterEqual(len(views), 4)
        self.assertTrue({"LEGAL_ENTITY", "INSTRUMENT_MASTER", "POSITION_SNAPSHOT", "TRADE"}.issubset(tables))
        self.assertTrue({"VW_POSITION_VALUATION", "VW_TRADE_LIFECYCLE", "VW_EXPOSURE_BY_COUNTERPARTY"}.issubset(views))

    def test_semantic_layer_uses_complex_views_as_base_tables(self):
        yaml_text = read(SEMANTIC_YAML)

        for view_name in [
            "VW_POSITION_VALUATION",
            "VW_INSTRUMENT_ENRICHED",
            "VW_TRADE_LIFECYCLE",
            "VW_EXPOSURE_BY_COUNTERPARTY",
        ]:
            self.assertIn(f"table: {view_name}", yaml_text)

    def test_relationships_reference_declared_logical_tables(self):
        yaml_text = read(SEMANTIC_YAML)
        table_names = logical_tables(yaml_text)

        self.assertTrue({"positions", "instruments", "legal_entities", "trades", "risk_exposures"}.issubset(table_names))
        self.assertTrue(relationship_table_refs(yaml_text))
        self.assertTrue(set(relationship_table_refs(yaml_text)).issubset(table_names))

    def test_semantic_layer_models_role_playing_parties_and_dates(self):
        yaml_text = read(SEMANTIC_YAML)

        for relationship in [
            "trades_to_buyers",
            "trades_to_sellers",
            "trades_to_brokers",
            "trades_to_counterparties",
            "positions_to_custodians",
            "instruments_to_issuers",
            "instruments_to_obligors",
        ]:
            self.assertIn(f"name: {relationship}", yaml_text)

        for date_field in ["as_of_date", "trade_date", "settlement_date", "exposure_date", "maturity_date"]:
            self.assertIn(f"name: {date_field}", yaml_text)

    def test_non_additive_metrics_are_marked_for_snapshot_values(self):
        yaml_text = read(SEMANTIC_YAML)

        self.assertIn("name: total_market_value_usd", yaml_text)
        self.assertIn('non_additive_dimensions: ["as_of_date"]', yaml_text)
        self.assertIn("name: total_exposure_amount_usd", yaml_text)
        self.assertIn('non_additive_dimensions: ["exposure_date"]', yaml_text)

    def test_verified_queries_cover_trend_and_role_ambiguity_surfaces(self):
        yaml_text = read(SEMANTIC_YAML)

        self.assertIn("verified_queries:", yaml_text)
        self.assertIn("market_value_by_issuer", yaml_text)
        self.assertIn("exposure_by_counterparty", yaml_text)
        self.assertIn("trade_notional_by_settlement_status", yaml_text)
        self.assertIn("latest as-of date", yaml_text)

    def test_cortex_instructions_split_sql_generation_and_question_categorization(self):
        cortex = read(CORTEX_SQL)

        self.assertIn("AI_SQL_GENERATION $$", cortex)
        self.assertIn("AI_QUESTION_CATEGORIZATION $$", cortex)
        self.assertIn("issuer, obligor, custodian, buyer, seller, broker, and counterparty", cortex)
        self.assertIn("Do not sum balances, market values, exposures, VaR, prices, or rates across dates", cortex)
        self.assertIn("Reject or explain unavailability for data outside this semantic view", cortex)

    def test_ontology_alignment_documents_confidence_and_boundaries(self):
        ontology = read(ONTOLOGY)

        for concept in [
            "Legal Entity Identifier",
            "Financial Instrument / Security",
            "Issuer role",
            "Obligor role",
            "Coupon rate",
            "Maturity date",
            "Notional amount",
        ]:
            self.assertIn(concept, ontology)

        self.assertIn("Physical joins still use warehouse columns", ontology)
        self.assertIn("Confidence is lower", ontology)

    def test_sql_generation_guardrails_are_documented(self):
        guardrails = read(GUARDRAILS)

        for required in [
            "Use only modeled metrics",
            "Do not invent a metric",
            "Do not create a join path",
            "Do not silently pick among multiple date fields",
            "Do not sum non-additive values across dates",
            "Bridge and Grouping Tables",
            "allocation_percent",
            "Semantic mapping",
        ]:
            self.assertIn(required, guardrails)

    def test_semantic_sql_prompt_template_requires_clarification(self):
        template = read(SQL_PROMPT_TEMPLATE)

        for required in [
            "Use $semantic-modeling",
            "Do not invent metrics, joins, filters, ontology mappings, or date defaults.",
            "ask for clarification instead of writing unsafe SQL",
            "apply modeled allocation, effective-date filters, or distinct logic",
            "Provide a semantic mapping summary before the SQL.",
        ]:
            self.assertIn(required, template)

    def test_neptune_reference_keeps_graph_and_metric_roles_separate(self):
        neptune = read(NEPTUNE_REF)

        for required in [
            "Use Neptune as the ontology and GraphRAG context layer",
            "Snowflake owns",
            "Metric answers such as AUM, exposure, balances, market value",
            "Never use GraphRAG context as proof of data availability.",
            "Neptune cannot create a Snowflake join",
            "Neptune cannot create a metric",
            "Use Snowflake SQL for questions like",
        ]:
            self.assertIn(required, neptune)

    def test_neptune_architecture_documents_inputs_processing_outputs(self):
        architecture = read(NEPTUNE_ARCH)

        for required in [
            "## Inputs",
            "## Processing Flow",
            "## Outputs",
            "Neptune is for meaning and disambiguation; Snowflake is for metrics.",
            "Ontology object properties do not imply physical joins.",
            "Missing semantic-model requirements should block SQL generation.",
        ]:
            self.assertIn(required, architecture)

    def test_neptune_examples_include_routing_and_sparql(self):
        routing = read(NEPTUNE_ROUTING)
        sparql = read(SPARQL_LOOKUPS)

        for required in [
            "Meaning Before SQL",
            "AUM by Account Group",
            "Ontology Relationship Without Warehouse Join",
            "do not invent a join",
        ]:
            self.assertIn(required, routing)

        for required in ["SELECT ?term ?label ?definition", "issuer", "legal entity identifier", "rdfs:subClassOf+"]:
            self.assertIn(required, sparql)


if __name__ == "__main__":
    unittest.main()
