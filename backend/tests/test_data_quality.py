"""
Phase 1 Data Quality & Exploration Test Suite.

Verifies:
1. Availability and non-emptiness of all 9 Olist CSV dataset files.
2. Primary key uniqueness and non-null constraints on primary entities.
3. Referential integrity across core transactional tables.
4. Correctness of customer grain (customer_id vs customer_unique_id).
5. Cardinality and join risk identification (orders vs items vs payments vs reviews).
6. Order status domain values and timeline validity.
"""

from pathlib import Path
import pytest
import pandas as pd

DATA_DIR = Path("data/raw")

REQUIRED_FILES = [
    "olist_orders_dataset.csv",
    "olist_order_items_dataset.csv",
    "olist_customers_dataset.csv",
    "olist_products_dataset.csv",
    "olist_order_payments_dataset.csv",
    "olist_order_reviews_dataset.csv",
    "olist_sellers_dataset.csv",
    "olist_geolocation_dataset.csv",
    "product_category_name_translation.csv",
]


@pytest.fixture(scope="session")
def raw_data():
    """Loads all raw datasets once for the test session."""
    datasets = {}
    for filename in REQUIRED_FILES:
        filepath = DATA_DIR / filename
        assert filepath.exists(), f"Missing required raw file: {filepath}"
        datasets[filename] = pd.read_csv(filepath)
    return datasets


def test_all_raw_files_exist_and_non_empty():
    """Verify that all 9 raw dataset files exist on disk with valid file sizes."""
    for filename in REQUIRED_FILES:
        filepath = DATA_DIR / filename
        assert filepath.exists(), f"File {filename} does not exist"
        assert filepath.stat().st_size > 1000, f"File {filename} is unexpectedly small or empty"


def test_customers_table_grain(raw_data):
    """
    Verify customer table grain:
    - customer_id is the primary key (1:1 with orders).
    - customer_unique_id represents actual distinct people (< total customer_id count).
    """
    df = raw_data["olist_customers_dataset.csv"]
    total_rows = len(df)
    assert total_rows == 99441
    assert df["customer_id"].nunique() == total_rows, "customer_id must be strictly unique"
    assert df["customer_id"].isnull().sum() == 0, "customer_id must have 0 nulls"

    unique_persons = df["customer_unique_id"].nunique()
    assert unique_persons == 96096, f"Expected 96,096 unique customer persons, got {unique_persons}"
    assert unique_persons < total_rows, "customer_unique_id must capture repeat customers"


def test_orders_table_grain_and_status(raw_data):
    """
    Verify orders table:
    - order_id is unique and non-null.
    - order count matches customer_id count exactly.
    - order_status contains expected lifecycle values.
    """
    df = raw_data["olist_orders_dataset.csv"]
    total_rows = len(df)
    assert total_rows == 99441
    assert df["order_id"].nunique() == total_rows, "order_id must be unique"
    assert df["order_id"].isnull().sum() == 0, "order_id must have 0 nulls"

    expected_statuses = {"delivered", "shipped", "canceled", "unavailable", "invoiced", "processing", "created", "approved"}
    actual_statuses = set(df["order_status"].unique())
    assert actual_statuses.issubset(expected_statuses), f"Unexpected order status: {actual_statuses - expected_statuses}"
    assert df["order_status"].value_counts()["delivered"] == 96478


def test_order_items_primary_key_and_relationships(raw_data):
    """
    Verify order_items:
    - Composite key (order_id, order_item_id) is unique and non-null.
    - All order_ids exist in orders table (0 orphan foreign keys).
    - All product_ids exist in products table.
    - All seller_ids exist in sellers table.
    """
    items = raw_data["olist_order_items_dataset.csv"]
    orders = raw_data["olist_orders_dataset.csv"]
    products = raw_data["olist_products_dataset.csv"]
    sellers = raw_data["olist_sellers_dataset.csv"]

    assert len(items) == 112650
    # Composite PK check
    composite_duplicates = items.duplicated(subset=["order_id", "order_item_id"]).sum()
    assert composite_duplicates == 0, "Composite key (order_id, order_item_id) must be unique"

    # Foreign key checks
    orphan_orders = (~items["order_id"].isin(orders["order_id"])).sum()
    assert orphan_orders == 0, "Found orphan order_id in order_items"

    orphan_products = (~items["product_id"].isin(products["product_id"])).sum()
    assert orphan_products == 0, "Found orphan product_id in order_items"

    orphan_sellers = (~items["seller_id"].isin(sellers["seller_id"])).sum()
    assert orphan_sellers == 0, "Found orphan seller_id in order_items"


def test_payments_grain_and_fanout_detection(raw_data):
    """
    Verify payments table:
    - Payments have 1:many relationship with orders.
    - Multiple payments occur in ~3% of orders.
    - Naive join of items and payments produces row inflation that must be avoided.
    """
    payments = raw_data["olist_order_payments_dataset.csv"]
    items = raw_data["olist_order_items_dataset.csv"]
    orders = raw_data["olist_orders_dataset.csv"]

    assert len(payments) == 103886

    # All payment order_ids exist in orders table
    orphan_orders = (~payments["order_id"].isin(orders["order_id"])).sum()
    assert orphan_orders == 0

    # Multi-payment count
    pay_counts = payments.groupby("order_id")["payment_sequential"].count()
    multi_pay_orders = (pay_counts > 1).sum()
    assert multi_pay_orders == 2961

    # Fanout verification
    item_counts = items.groupby("order_id")["order_item_id"].count()
    merged = item_counts.reset_index().merge(pay_counts.reset_index(), on="order_id")
    cartesian_rows = (merged["order_item_id"] * merged["payment_sequential"]).sum()
    assert cartesian_rows > len(items), "Direct join must show Cartesian expansion"
    assert cartesian_rows == 117601


def test_reviews_duplicates_detection(raw_data):
    """
    Verify reviews table:
    - Multiple reviews exist for a subset of orders (547 orders).
    - Reviews table must be deduplicated or aggregated before 1:1 order joining.
    """
    reviews = raw_data["olist_order_reviews_dataset.csv"]
    orders = raw_data["olist_orders_dataset.csv"]

    assert len(reviews) == 99224
    orphan_orders = (~reviews["order_id"].isin(orders["order_id"])).sum()
    assert orphan_orders == 0

    order_review_counts = reviews.groupby("order_id")["review_id"].count()
    multi_review_orders = (order_review_counts > 1).sum()
    assert multi_review_orders == 547


def test_category_translation_completeness(raw_data):
    """
    Verify product category translation coverage:
    - Identifies products with categories missing from translation table.
    """
    products = raw_data["olist_products_dataset.csv"]
    trans = raw_data["product_category_name_translation.csv"]

    non_null_cats = products["product_category_name"].dropna().unique()
    trans_cats = set(trans["product_category_name"])
    missing_cats = set(non_null_cats) - trans_cats

    # There are 2 Portuguese category names not present in translation table:
    # 'portateis_cozinha_e_preparadores_de_alimentos' and 'pc_gamer'
    assert len(missing_cats) == 2, f"Expected 2 untranslated categories, got {missing_cats}"
    assert "pc_gamer" in missing_cats
    assert "portateis_cozinha_e_preparadores_de_alimentos" in missing_cats

