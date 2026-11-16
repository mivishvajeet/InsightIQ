"""
High-Performance Raw Data Ingestion Service for InsightIQ.

Loads all 9 raw Olist CSV datasets into PostgreSQL `raw.*` tables
with proper data type casting, null handling, and foreign-key ordered loading.
"""

import io
import os
import sys
import time
from pathlib import Path
from typing import Dict, Any

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
import psycopg2
from sqlalchemy import text
from backend.app.services.database import admin_engine, POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD

DATA_DIR = Path("data/raw")


class DataLoader:
    """Handles schema creation and bulk CSV data ingestion into PostgreSQL."""

    def __init__(self, data_dir: Path | str = DATA_DIR):
        self.data_dir = Path(data_dir)

    def init_schema(self, ddl_path: Path = Path("database/schema/01_raw_schema.sql")):
        """Executes the raw DDL schema script."""
        with open(ddl_path, "r", encoding="utf-8") as f:
            ddl_sql = f.read()

        with admin_engine.connect() as conn:
            conn.execute(text(ddl_sql))
            conn.commit()
        print("Raw schema and indexes successfully initialized.")

    def bulk_copy_df(self, conn, table_name: str, df: pd.DataFrame):
        """Uses PostgreSQL COPY protocol via io.StringIO for maximum ingestion speed."""
        output = io.StringIO()
        # Export dataframe to CSV in-memory buffer without index and with NULL represented as empty
        df.to_csv(output, sep="\t", header=False, index=False, na_rep="\\N")
        output.seek(0)

        cursor = conn.cursor()
        columns = [f'"{col}"' for col in df.columns]
        cols_str = ", ".join(columns)
        sql = f"COPY raw.{table_name} ({cols_str}) FROM STDIN WITH (FORMAT CSV, DELIMITER E'\\t', NULL '\\N')"
        cursor.copy_expert(sql, output)
        conn.commit()
        cursor.close()

    def clean_products_df(self, df: pd.DataFrame) -> pd.DataFrame:
        """Ensures nullable integer columns in products are formatted as Int64."""
        int_cols = ["product_name_lenght", "product_description_lenght", "product_photos_qty"]
        for col in int_cols:
            if col in df.columns:
                df[col] = df[col].astype("Int64")
        return df

    def truncate_raw(self, conn):
        """Safely truncates all raw tables before loading to ensure idempotency."""
        cursor = conn.cursor()
        cursor.execute(
            """
            TRUNCATE TABLE 
                raw.order_reviews,
                raw.order_payments,
                raw.order_items,
                raw.orders,
                raw.products,
                raw.sellers,
                raw.customers,
                raw.geolocation,
                raw.product_category_name_translation
            CASCADE;
            """
        )
        conn.commit()
        cursor.close()

    def ingest_all(self) -> Dict[str, Any]:
        """Loads all raw datasets into PostgreSQL raw schema in topological order."""
        start_time = time.time()
        print("Starting raw data ingestion into PostgreSQL...")

        conn = psycopg2.connect(
            host=POSTGRES_HOST,
            port=POSTGRES_PORT,
            dbname=POSTGRES_DB,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD
        )

        results = {}

        try:
            self.truncate_raw(conn)

            # 1. Customers
            print("  Ingesting raw.customers ...")
            df_cust = pd.read_csv(self.data_dir / "olist_customers_dataset.csv")
            self.bulk_copy_df(conn, "customers", df_cust)
            results["customers"] = len(df_cust)

            # 2. Orders
            print("  Ingesting raw.orders ...")
            df_orders = pd.read_csv(self.data_dir / "olist_orders_dataset.csv")
            self.bulk_copy_df(conn, "orders", df_orders)
            results["orders"] = len(df_orders)

            # 3. Products
            print("  Ingesting raw.products ...")
            df_prod = pd.read_csv(self.data_dir / "olist_products_dataset.csv")
            df_prod = self.clean_products_df(df_prod)
            self.bulk_copy_df(conn, "products", df_prod)
            results["products"] = len(df_prod)

            # 4. Sellers
            print("  Ingesting raw.sellers ...")
            df_sellers = pd.read_csv(self.data_dir / "olist_sellers_dataset.csv")
            self.bulk_copy_df(conn, "sellers", df_sellers)
            results["sellers"] = len(df_sellers)

            # 5. Order Items
            print("  Ingesting raw.order_items ...")
            df_items = pd.read_csv(self.data_dir / "olist_order_items_dataset.csv")
            self.bulk_copy_df(conn, "order_items", df_items)
            results["order_items"] = len(df_items)

            # 6. Payments
            print("  Ingesting raw.order_payments ...")
            df_pay = pd.read_csv(self.data_dir / "olist_order_payments_dataset.csv")
            self.bulk_copy_df(conn, "order_payments", df_pay)
            results["order_payments"] = len(df_pay)

            # 7. Reviews
            print("  Ingesting raw.order_reviews ...")
            df_rev = pd.read_csv(self.data_dir / "olist_order_reviews_dataset.csv")
            self.bulk_copy_df(conn, "order_reviews", df_rev)
            results["order_reviews"] = len(df_rev)

            # 8. Geolocation
            print("  Ingesting raw.geolocation (1,000,163 rows) ...")
            df_geo = pd.read_csv(self.data_dir / "olist_geolocation_dataset.csv")
            self.bulk_copy_df(conn, "geolocation", df_geo)
            results["geolocation"] = len(df_geo)

            # 9. Category Translation
            print("  Ingesting raw.product_category_name_translation ...")
            df_trans = pd.read_csv(self.data_dir / "product_category_name_translation.csv")
            self.bulk_copy_df(conn, "product_category_name_translation", df_trans)
            results["product_category_name_translation"] = len(df_trans)

        finally:
            conn.close()

        elapsed = time.time() - start_time
        print(f"\nAll 9 tables ingested in {elapsed:.2f} seconds!")
        return results

    def verify_counts(self) -> Dict[str, Dict[str, int]]:
        """Verifies row counts in raw schema match the original CSV counts."""
        tables = [
            "customers", "orders", "products", "sellers",
            "order_items", "order_payments", "order_reviews",
            "geolocation", "product_category_name_translation"
        ]
        comparison = {}
        with admin_engine.connect() as conn:
            for t in tables:
                db_count = conn.execute(text(f"SELECT COUNT(*) FROM raw.{t};")).scalar()
                comparison[t] = {"database_count": db_count}

        return comparison


if __name__ == "__main__":
    loader = DataLoader()
    loader.init_schema()
    counts = loader.ingest_all()
    verification = loader.verify_counts()
    for table, data in verification.items():
        print(f"  {table:35s}: {data['database_count']:>8,} rows in DB")
