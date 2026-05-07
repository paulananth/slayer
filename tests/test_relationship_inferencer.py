import unittest

from tools.relationship_inferencer import (
    ExplicitRelationship,
    InferenceColumn,
    InferenceTable,
    infer_relationships,
)


class RelationshipInferencerTests(unittest.TestCase):
    def test_explicit_relationships_win_and_skip_unsafe_model_edges(self):
        tables = [
            InferenceTable(
                "sales",
                source_name="Sales",
                columns=[
                    InferenceColumn("customer_key", "CustomerKey"),
                    InferenceColumn("product_key", "ProductKey"),
                ],
            ),
            InferenceTable(
                "customer",
                source_name="Customer",
                columns=[InferenceColumn("customer_key", "CustomerKey", is_unique=True)],
            ),
            InferenceTable(
                "product",
                source_name="Product",
                columns=[InferenceColumn("product_key", "ProductKey", is_unique=True)],
            ),
        ]

        result = infer_relationships(
            tables,
            [
                ExplicitRelationship(
                    "Sales",
                    "CustomerKey",
                    "Customer",
                    "CustomerKey",
                    cardinality="ManyToOne",
                    source="Power BI",
                ),
                ExplicitRelationship(
                    "Sales",
                    "ProductKey",
                    "Product",
                    "ProductKey",
                    cardinality="ManyToMany",
                    source="Power BI",
                ),
            ],
        )

        self.assertEqual(len(result.relationships), 1)
        rel = result.relationships[0]
        self.assertEqual(rel.source, "explicit")
        self.assertEqual(rel.name, "sales_to_customer")
        self.assertEqual(rel.left_column, "customer_key")
        self.assertEqual(rel.right_column, "customer_key")
        self.assertIn("Skipped many-to-many Power BI relationship", "\n".join(result.warnings))

    def test_infers_role_playing_party_relationships(self):
        tables = [
            InferenceTable(
                "trades",
                columns=[
                    InferenceColumn("buyer_id"),
                    InferenceColumn("seller_id"),
                    InferenceColumn("broker_id"),
                ],
            ),
            InferenceTable(
                "parties",
                columns=[InferenceColumn("party_id", is_unique=True)],
            ),
        ]

        result = infer_relationships(tables)
        names = {rel.name for rel in result.relationships}

        self.assertTrue({"trades_to_buyers", "trades_to_sellers", "trades_to_brokers"}.issubset(names))
        self.assertFalse(result.warnings)

    def test_skips_ambiguous_inferred_relationships(self):
        tables = [
            InferenceTable("orders", columns=[InferenceColumn("customer_id")]),
            InferenceTable("customers", columns=[InferenceColumn("customer_id", is_unique=True)]),
            InferenceTable("customer_archive", columns=[InferenceColumn("customer_id", is_unique=True)]),
        ]

        result = infer_relationships(tables)

        self.assertFalse(result.relationships)
        self.assertIn("Skipped ambiguous relationship for orders.customer_id", "\n".join(result.warnings))


if __name__ == "__main__":
    unittest.main()
