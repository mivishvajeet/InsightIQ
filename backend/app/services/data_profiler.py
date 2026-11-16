"""
Data Profiler & Quality Assessment Service for InsightIQ.

Performs deep profiling on the Brazilian E-Commerce (Olist) dataset:
- Table dimensions, column types, and memory usage
- Missing value profiling
- Primary key candidate verification
- Foreign key referential integrity check
- Cardinality analysis (especially orders vs items vs payments)
- Temporal range analysis
- Statistical anomalies and quality warnings
"""

import json
from pathlib import Path
from typing import Any, Dict, List
import numpy as np
import pandas as pd


class DataProfiler:
    """Profiles raw Olist CSV datasets and assesses data quality."""

    def __init__(self, data_dir: Path | str = Path("data/raw")):
        self.data_dir = Path(data_dir)
        self.datasets: Dict[str, pd.DataFrame] = {}
        self.file_names = {
            "orders": "olist_orders_dataset.csv",
            "order_items": "olist_order_items_dataset.csv",
            "customers": "olist_customers_dataset.csv",
            "products": "olist_products_dataset.csv",
            "payments": "olist_order_payments_dataset.csv",
            "reviews": "olist_order_reviews_dataset.csv",
            "sellers": "olist_sellers_dataset.csv",
            "geolocation": "olist_geolocation_dataset.csv",
            "category_translation": "product_category_name_translation.csv",
        }

    def load_data(self) -> Dict[str, pd.DataFrame]:
        """Loads all raw datasets into memory."""
        for key, filename in self.file_names.items():
            path = self.data_dir / filename
            if not path.exists():
                raise FileNotFoundError(f"Missing required dataset: {path}")
            self.datasets[key] = pd.read_csv(path)
        return self.datasets

    def profile_tables(self) -> Dict[str, Any]:
        """Profiles each table's schema, row count, nulls, and unique keys."""
        if not self.datasets:
            self.load_data()

        profiles = {}
        for key, df in self.datasets.items():
            cols_info = []
            for col in df.columns:
                null_count = int(df[col].isnull().sum())
                null_pct = float((null_count / len(df)) * 100) if len(df) > 0 else 0.0
                unique_count = int(df[col].nunique(dropna=False))
                cols_info.append(
                    {
                        "column": col,
                        "dtype": str(df[col].dtype),
                        "null_count": null_count,
                        "null_pct": round(null_pct, 2),
                        "unique_count": unique_count,
                    }
                )

            profiles[key] = {
                "file_name": self.file_names[key],
                "row_count": len(df),
                "column_count": len(df.columns),
                "columns": cols_info,
            }
        return profiles

    def check_primary_keys(self) -> Dict[str, Dict[str, Any]]:
        """Verifies primary key candidates and uniqueness."""
        if not self.datasets:
            self.load_data()

        expected_keys = {
            "customers": ["customer_id"],
            "orders": ["order_id"],
            "order_items": ["order_id", "order_item_id"],
            "products": ["product_id"],
            "sellers": ["seller_id"],
            "category_translation": ["product_category_name"],
        }

        results = {}
        for table, pk_cols in expected_keys.items():
            df = self.datasets[table]
            total_rows = len(df)
            distinct_rows = len(df.drop_duplicates(subset=pk_cols))
            is_unique = (total_rows == distinct_rows)
            null_count = int(df[pk_cols].isnull().any(axis=1).sum())

            results[table] = {
                "key_columns": pk_cols,
                "total_rows": total_rows,
                "distinct_keys": distinct_rows,
                "is_unique": is_unique,
                "null_keys": null_count,
                "is_valid_pk": is_unique and (null_count == 0),
            }
        return results

    def check_referential_integrity(self) -> Dict[str, Any]:
        """Checks foreign key relationships between tables."""
        if not self.datasets:
            self.load_data()

        relationships = [
            ("orders", "customer_id", "customers", "customer_id"),
            ("order_items", "order_id", "orders", "order_id"),
            ("order_items", "product_id", "products", "product_id"),
            ("order_items", "seller_id", "sellers", "seller_id"),
            ("payments", "order_id", "orders", "order_id"),
            ("reviews", "order_id", "orders", "order_id"),
            ("products", "product_category_name", "category_translation", "product_category_name"),
        ]

        integrity_results = []
        for child_table, child_col, parent_table, parent_col in relationships:
            child_df = self.datasets[child_table]
            parent_df = self.datasets[parent_table]

            # Filter out null child values if nullable
            child_vals = child_df[child_col].dropna()
            parent_keys = set(parent_df[parent_col].dropna().unique())

            orphan_mask = ~child_vals.isin(parent_keys)
            orphan_count = int(orphan_mask.sum())
            orphan_pct = float(round((orphan_count / len(child_vals)) * 100, 3)) if len(child_vals) > 0 else 0.0

            integrity_results.append(
                {
                    "relationship": f"{child_table}.{child_col} -> {parent_table}.{parent_col}",
                    "child_table": child_table,
                    "child_column": child_col,
                    "parent_table": parent_table,
                    "parent_column": parent_col,
                    "child_non_null_records": len(child_vals),
                    "orphan_records": orphan_count,
                    "orphan_pct": orphan_pct,
                    "referential_integrity_holds": (orphan_count == 0),
                }
            )
        return {"relationships": integrity_results}

    def analyze_order_cardinality(self) -> Dict[str, Any]:
        """Analyzes cardinality between orders, items, and payments to prevent fan-out in SQL."""
        if not self.datasets:
            self.load_data()

        orders_df = self.datasets["orders"]
        items_df = self.datasets["order_items"]
        payments_df = self.datasets["payments"]

        # Items per order distribution
        items_per_order = items_df.groupby("order_id")["order_item_id"].count()
        payments_per_order = payments_df.groupby("order_id")["payment_sequential"].count()

        multi_item_orders = int((items_per_order > 1).sum())
        multi_payment_orders = int((payments_per_order > 1).sum())

        # Total order counts
        total_unique_orders = int(orders_df["order_id"].nunique())
        orders_with_items = int(items_per_order.index.nunique())
        orders_with_payments = int(payments_per_order.index.nunique())

        # Calculate potential cartesian explosion if joined directly on order_id
        items_count_df = items_per_order.reset_index(name="item_count")
        payments_count_df = payments_per_order.reset_index(name="payment_count")
        joined = items_count_df.merge(payments_count_df, on="order_id", how="inner")
        direct_join_rows = int((joined["item_count"] * joined["payment_count"]).sum())
        actual_items_rows = len(items_df)
        actual_payment_rows = len(payments_df)

        return {
            "total_orders": total_unique_orders,
            "orders_with_items": orders_with_items,
            "orders_without_items": total_unique_orders - orders_with_items,
            "orders_with_payments": orders_with_payments,
            "orders_without_payments": total_unique_orders - orders_with_payments,
            "multi_item_orders_count": multi_item_orders,
            "multi_item_orders_pct": round(multi_item_orders / orders_with_items * 100, 2),
            "max_items_in_single_order": int(items_per_order.max()),
            "multi_payment_orders_count": multi_payment_orders,
            "multi_payment_orders_pct": round(multi_payment_orders / orders_with_payments * 100, 2),
            "max_payments_in_single_order": int(payments_per_order.max()),
            "actual_order_items_rows": actual_items_rows,
            "actual_payments_rows": actual_payment_rows,
            "naive_direct_join_rows": direct_join_rows,
            "row_multiplication_factor": round(direct_join_rows / max(actual_items_rows, 1), 3),
            "warning": (
                "Directly joining fact_order_items with fact_payments on order_id causes a Cartesian "
                "fan-out. Revenue and payment aggregations MUST be modeled at separate grains or pre-aggregated."
            ),
        }

    def analyze_order_status_and_dates(self) -> Dict[str, Any]:
        """Analyzes order status breakdown and date timelines."""
        if not self.datasets:
            self.load_data()

        orders_df = self.datasets["orders"].copy()
        date_cols = [
            "order_purchase_timestamp",
            "order_approved_at",
            "order_delivered_carrier_date",
            "order_delivered_customer_date",
            "order_estimated_delivery_date",
        ]
        for col in date_cols:
            orders_df[col] = pd.to_datetime(orders_df[col], errors="coerce")

        status_counts = orders_df["order_status"].value_counts().to_dict()
        status_pcts = {
            k: round(v / len(orders_df) * 100, 2) for k, v in status_counts.items()
        }

        min_purchase = orders_df["order_purchase_timestamp"].min()
        max_purchase = orders_df["order_purchase_timestamp"].max()

        delivered = orders_df[orders_df["order_status"] == "delivered"]
        delivered_missing_actual = int(delivered["order_delivered_customer_date"].isnull().sum())

        return {
            "total_orders": len(orders_df),
            "status_distribution": status_counts,
            "status_percentages": status_pcts,
            "min_purchase_timestamp": str(min_purchase),
            "max_purchase_timestamp": str(max_purchase),
            "delivered_orders_total": int(len(delivered)),
            "delivered_orders_missing_delivery_date": delivered_missing_actual,
        }

    def generate_full_report(self) -> Dict[str, Any]:
        """Generates comprehensive profiling summary."""
        return {
            "tables": self.profile_tables(),
            "primary_keys": self.check_primary_keys(),
            "referential_integrity": self.check_referential_integrity(),
            "cardinality": self.analyze_order_cardinality(),
            "order_status_and_dates": self.analyze_order_status_and_dates(),
        }


if __name__ == "__main__":
    profiler = DataProfiler()
    report = profiler.generate_full_report()
    out_path = Path("data/processed/phase1_data_profile_report.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"Data profiling report generated at: {out_path}")

