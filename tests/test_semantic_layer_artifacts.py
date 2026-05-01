import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples" / "complex-financial-model"
SCHEMA_SQL = EXAMPLE / "schema.sql"
SEMANTIC_YAML = EXAMPLE / "semantic-view.yaml"
CORTEX_SQL = EXAMPLE / "cortex-instructions.sql"
ONTOLOGY = EXAMPLE / "ontology-alignment.md"


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


if __name__ == "__main__":
    unittest.main()
