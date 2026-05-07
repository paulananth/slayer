import unittest

import yaml

from tools.pbixray_semantic_converter import (
    PbiColumn,
    PbiMeasure,
    PbiRelationship,
    convert_powerbi_model,
)


class PbixraySemanticConverterTests(unittest.TestCase):
    def test_converts_pbix_model_to_snowflake_semantic_view_artifacts(self):
        result = convert_powerbi_model(
            tables=["Sales", "Customer", "Date", "Measures"],
            columns=[
                PbiColumn("Sales", "SalesKey", "int64", is_hidden=True),
                PbiColumn("Sales", "CustomerKey", "int64", is_hidden=True),
                PbiColumn("Sales", "DateKey", "int64", is_hidden=True),
                PbiColumn("Sales", "OrderDate", "datetime64[ns]"),
                PbiColumn("Sales", "NetAmount", "float64"),
                PbiColumn("Customer", "CustomerKey", "int64", is_hidden=True),
                PbiColumn("Customer", "CustomerName", "object"),
                PbiColumn("Date", "DateKey", "int64", is_hidden=True),
                PbiColumn("Date", "FiscalYear", "int64"),
            ],
            relationships=[
                PbiRelationship(
                    from_table="Sales",
                    from_column="CustomerKey",
                    to_table="Customer",
                    to_column="CustomerKey",
                    cardinality="ManyToOne",
                ),
                PbiRelationship(
                    from_table="Sales",
                    from_column="DateKey",
                    to_table="Date",
                    to_column="DateKey",
                    cardinality="ManyToOne",
                ),
            ],
            measures=[
                PbiMeasure("Measures", "Total Sales", "SUM('Sales'[NetAmount])"),
                PbiMeasure("Measures", "Sales Count", "COUNTROWS(Sales)"),
                PbiMeasure("Measures", "Unsupported Filtered Sales", "CALCULATE([Total Sales], Sales[NetAmount] > 0)"),
            ],
            extras={"rls": [{"TableName": "Sales", "RoleName": "Region"}]},
            snowflake_database="analytics",
            snowflake_schema="mart_sales",
            view_name="sales_semantic_view",
            table_map={"Sales": "FACT_SALES", "Customer": "DIM_CUSTOMER", "Date": "DIM_DATE"},
        )

        doc = yaml.safe_load(result.yaml_content)

        self.assertEqual(result.root_table, "Sales")
        self.assertEqual(doc["name"], "sales_semantic_view")
        self.assertEqual(doc["tables"][0]["name"], "sales")
        self.assertEqual(doc["tables"][0]["base_table"]["table"], "FACT_SALES")

        relationship_names = {rel["name"] for rel in doc["relationships"]}
        self.assertIn("sales_to_customer", relationship_names)
        self.assertIn("sales_to_date", relationship_names)

        sales_metrics = {
            metric["name"]: metric["expr"]
            for table in doc["tables"]
            if table["name"] == "sales"
            for metric in table["metrics"]
        }
        self.assertEqual(sales_metrics["total_sales"], "SUM(net_amount)")
        self.assertEqual(sales_metrics["sales_count"], "COUNT(*)")

        self.assertIn("SYSTEM$CREATE_SEMANTIC_VIEW_FROM_YAML", result.sql_content)
        self.assertIn("TRUE", result.sql_content)
        self.assertIn("## 5-Whys", result.notes_content)
        self.assertIn("Skipped unsupported DAX measure", result.notes_content)
        self.assertIn("Power BI RLS was found", result.notes_content)

    def test_requested_root_table_must_exist(self):
        with self.assertRaisesRegex(ValueError, "Requested root table"):
            convert_powerbi_model(
                tables=["Sales"],
                columns=[PbiColumn("Sales", "Amount", "float64")],
                relationships=[],
                measures=[],
                extras={},
                snowflake_database="ANALYTICS",
                snowflake_schema="PUBLIC",
                view_name="bad_root",
                root_table="Missing",
            )


if __name__ == "__main__":
    unittest.main()
