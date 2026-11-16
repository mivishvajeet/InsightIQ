"""
Generates the Phase 1 Jupyter Notebook: notebooks/01_phase1_data_exploration.ipynb
"""
import json
from pathlib import Path

notebook_content = {
    "cells": [
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "# InsightIQ: Phase 1 - Dataset Exploration & Data Quality Assessment\n",
                "## Brazilian E-Commerce Public Dataset by Olist\n",
                "\n",
                "This notebook performs exploratory data analysis (EDA), grain validation, referential integrity verification, and cardinality analysis on the raw Olist datasets."
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "import pandas as pd\n",
                "import numpy as np\n",
                "from pathlib import Path\n",
                "import json\n",
                "\n",
                "DATA_DIR = Path('../data/raw')\n",
                "print('Data directory exists:', DATA_DIR.exists())"
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "### 1. Load All 9 Raw Datasets"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "datasets = {\n",
                "    'orders': pd.read_csv(DATA_DIR / 'olist_orders_dataset.csv'),\n",
                "    'order_items': pd.read_csv(DATA_DIR / 'olist_order_items_dataset.csv'),\n",
                "    'customers': pd.read_csv(DATA_DIR / 'olist_customers_dataset.csv'),\n",
                "    'products': pd.read_csv(DATA_DIR / 'olist_products_dataset.csv'),\n",
                "    'payments': pd.read_csv(DATA_DIR / 'olist_order_payments_dataset.csv'),\n",
                "    'reviews': pd.read_csv(DATA_DIR / 'olist_order_reviews_dataset.csv'),\n",
                "    'sellers': pd.read_csv(DATA_DIR / 'olist_sellers_dataset.csv'),\n",
                "    'geolocation': pd.read_csv(DATA_DIR / 'olist_geolocation_dataset.csv'),\n",
                "    'category_translation': pd.read_csv(DATA_DIR / 'product_category_name_translation.csv')\n",
                "}\n",
                "\n",
                "for name, df in datasets.items():\n",
                "    print(f\"{name:20s}: {len(df):>8,} rows, {len(df.columns)} columns\")"
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "### 2. Customer Grain Validation (`customer_id` vs `customer_unique_id`)\n",
                "Verifies that `customer_id` is an order token (1:1 with orders) whereas `customer_unique_id` represents unique individuals."
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "customers = datasets['customers']\n",
                "total_records = len(customers)\n",
                "unique_persons = customers['customer_unique_id'].nunique()\n",
                "repeat_persons = (customers['customer_unique_id'].value_counts() > 1).sum()\n",
                "\n",
                "print(f\"Total customer records: {total_records:,}\")\n",
                "print(f\"Distinct unique individuals: {unique_persons:,}\")\n",
                "print(f\"Repeat customers (>1 order): {repeat_persons:,}\")\n",
                "print(f\"Repeat purchase rate: {repeat_persons / unique_persons * 100:.2f}%\")"
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "### 3. Join Cardinality & Fan-Out Analysis\n",
                "Demonstrating why naively joining `order_items` and `order_payments` creates artificial revenue inflation."
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "items = datasets['order_items']\n",
                "payments = datasets['payments']\n",
                "\n",
                "items_per_order = items.groupby('order_id')['order_item_id'].count().reset_index(name='items_count')\n",
                "pay_per_order = payments.groupby('order_id')['payment_sequential'].count().reset_index(name='payments_count')\n",
                "direct_join = items_per_order.merge(pay_per_order, on='order_id')\n",
                "cartesian_rows = (direct_join['items_count'] * direct_join['payments_count']).sum()\n",
                "\n",
                "print(f\"Actual order item rows: {len(items):,}\")\n",
                "print(f\"Actual payment rows:    {len(payments):,}\")\n",
                "print(f\"Naive direct join rows: {cartesian_rows:,}\")\n",
                "print(f\"Inflation factor:       {cartesian_rows / len(items):.3f}x\")"
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "### 4. Revenue Baseline Verification\n",
                "Comparing Delivered Items (Price + Freight) vs Delivered Payments."
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "orders = datasets['orders']\n",
                "delivered_order_ids = set(orders[orders['order_status'] == 'delivered']['order_id'])\n",
                "\n",
                "delivered_items = items[items['order_id'].isin(delivered_order_ids)]\n",
                "delivered_payments = payments[payments['order_id'].isin(delivered_order_ids)]\n",
                "\n",
                "item_price_sum = delivered_items['price'].sum()\n",
                "item_freight_sum = delivered_items['freight_value'].sum()\n",
                "total_items_rev = item_price_sum + item_freight_sum\n",
                "total_payments_rev = delivered_payments['payment_value'].sum()\n",
                "\n",
                "print(f\"Delivered GMV (Item price only):     R$ {item_price_sum:,.2f}\")\n",
                "print(f\"Delivered Freight:                   R$ {item_freight_sum:,.2f}\")\n",
                "print(f\"Delivered Total (Price + Freight):   R$ {total_items_rev:,.2f}\")\n",
                "print(f\"Delivered Total (Payment values):    R$ {total_payments_rev:,.2f}\")\n",
                "print(f\"Discrepancy (Vouchers / rounding):   R$ {abs(total_items_rev - total_payments_rev):,.2f}\")"
            ]
        }
    ],
    "metadata": {
        "language_info": {
            "name": "python"
        }
    },
    "nbformat": 4,
    "nbformat_minor": 2
}

nb_path = Path("notebooks/01_phase1_data_exploration.ipynb")
with open(nb_path, "w", encoding="utf-8") as f:
    json.dump(notebook_content, f, indent=2)

print(f"Jupyter Notebook generated at: {nb_path}")
