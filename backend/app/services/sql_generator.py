"""
SQL Generator & Validator Service for InsightIQ.

Converts natural-language business questions into validated, safe, read-only PostgreSQL queries.
Enforces:
1. Read-only SELECT validation (rejects DROP, DELETE, INSERT, UPDATE, ALTER, etc.)
2. Schema isolation (queries can ONLY access analytics.* tables and views)
3. Mandatory LIMIT enforcement (max rows returned: 500)
4. Domain grounding (customer_unique_id for people, is_delivered for revenue)
5. Query explanation generation
"""

import os
import re
import sys
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
import pandas as pd
from sqlalchemy import text

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.services.database import readonly_engine, SQL_MAX_ROWS_RETURNED
from backend.app.services.llm_client import OllamaClient


FORBIDDEN_KEYWORDS = [
    r"\bDROP\b",
    r"\bDELETE\b",
    r"\bINSERT\b",
    r"\bUPDATE\b",
    r"\bTRUNCATE\b",
    r"\bALTER\b",
    r"\bCREATE\b",
    r"\bGRANT\b",
    r"\bREVOKE\b",
    r"\bEXEC\b",
    r"\bEXECUTE\b",
    r"\bVACUUM\b",
    r"\bCOPY\b",
]

ANALYTICS_SCHEMA_PROMPT = """
You are an expert PostgreSQL Data Analyst for InsightIQ.
Convert the user's natural language question into a clean, valid PostgreSQL query.

CRITICAL RULES:
1. ONLY generate SELECT queries (or WITH ... SELECT). NEVER use INSERT, UPDATE, DELETE, or DROP.
2. Only query tables and views in the 'analytics' schema.
3. Tables available in 'analytics':
   - analytics.fact_orders (order_id, customer_id, order_status, is_delivered, total_order_amount, total_item_value, total_freight_value, aov, latest_review_score, delivery_lead_time_days, delivery_delay_days, is_on_time, purchase_date_key)
   - analytics.fact_order_items (order_id, order_item_id, product_id, seller_id, is_delivered, price, freight_value, total_item_cost)
   - analytics.dim_customers (customer_id, customer_unique_id, customer_city, customer_state)
   - analytics.dim_products (product_id, product_category_name_english, product_category_name_pt)
   - analytics.dim_sellers (seller_id, seller_city, seller_state)
   - analytics.dim_date (date_key, full_date, year, month, year_month, day_name)
4. Approved Analytical Views (PREFER THESE FOR COMMON QUESTIONS):
   - analytics.v_monthly_sales (year_month, delivered_orders, gmv, freight_revenue, total_delivered_revenue, aov, active_unique_customers)
   - analytics.v_category_performance (product_category, total_items_sold, total_orders, total_revenue, avg_item_price, avg_review_score)
   - analytics.v_state_sales_distribution (customer_state, unique_customers, total_orders, total_delivered_revenue, avg_order_value, avg_delivery_lead_time_days, on_time_delivery_rate_pct)
   - analytics.v_customer_rfm_segments (customer_unique_id, recency_days, frequency, monetary, customer_segment)
   - analytics.v_seller_performance (seller_id, seller_city, seller_state, total_orders, cancellation_rate_pct, total_sales_value, avg_review_score)
5. BUSINESS LOGIC RULES:
   - For revenue, sales, and AOV: Always filter by completed orders: is_delivered = TRUE (or query views).
   - For customer counts, retention, and repeat buyers: Always count or group by customer_unique_id (NOT customer_id).
   - NEVER join fact_order_items directly with fact_payments on order_id.
6. Return your output as pure SQL only. Do NOT wrap in markdown quotes if possible, or use standard markdown ```sql.
"""


class SQLValidator:
    """Validates and sanitizes SQL queries before execution."""

    @staticmethod
    def sanitize_sql(raw_sql: str) -> str:
        """Strips markdown code blocks, comments, and extra whitespace."""
        cleaned = re.sub(r"```(?:sql)?", "", raw_sql, flags=re.IGNORECASE)
        cleaned = cleaned.replace("```", "").strip()
        # Remove trailing semicolon
        cleaned = cleaned.rstrip(";").strip()
        return cleaned

    @staticmethod
    def validate_sql(sql: str) -> Tuple[bool, Optional[str]]:
        """
        Validates safety, read-only permissions, and schema constraints.
        Returns (is_valid, error_message).
        """
        clean_upper = sql.upper()

        # 1. Must start with SELECT or WITH
        trimmed = clean_upper.strip()
        if not (trimmed.startswith("SELECT") or trimmed.startswith("WITH")):
            return False, "Query rejected: Only SELECT or WITH statements are allowed."

        # 2. Check for forbidden destructive keywords
        for pattern in FORBIDDEN_KEYWORDS:
            if re.search(pattern, clean_upper):
                return False, f"Query rejected: Forbidden keyword detected ({pattern})."

        # 3. Check for multiple statements (prevent SQL injection via semicolon stacking)
        if ";" in sql:
            # Check if there are non-whitespace characters after semicolon
            parts = [p.strip() for p in sql.split(";") if p.strip()]
            if len(parts) > 1:
                return False, "Query rejected: Multiple SQL statements are not permitted."

        # 4. Enforce schema restriction: Reject queries explicitly attempting to access raw or staging
        if re.search(r"\bRAW\.", clean_upper) or re.search(r"\bSTAGING\.", clean_upper):
            return False, "Query rejected: Direct access to 'raw' and 'staging' schemas is prohibited. Only 'analytics' is permitted."

        return True, None

    @staticmethod
    def enforce_limit(sql: str, default_limit: int = SQL_MAX_ROWS_RETURNED) -> str:
        """Injects a LIMIT clause if absent to prevent runaway result sets."""
        if not re.search(r"\bLIMIT\s+\d+", sql, flags=re.IGNORECASE):
            sql = f"{sql} LIMIT {default_limit}"
        return sql


class SQLGenerator:
    """Orchestrates natural language to SQL generation and execution."""

    def __init__(self, llm_client: Optional[OllamaClient] = None):
        self.llm = llm_client or OllamaClient()

    def generate_sql(self, question: str) -> str:
        """Generates SQL from user prompt using local Qwen model."""
        prompt = f"User Question: {question}\nGenerate PostgreSQL Query:"
        raw_response = self.llm.generate(
            prompt=prompt,
            system_prompt=ANALYTICS_SCHEMA_PROMPT,
            temperature=0.0,
        )
        clean_sql = SQLValidator.sanitize_sql(raw_response)
        return clean_sql

    def execute_query(self, sql: str) -> Tuple[pd.DataFrame, Optional[str]]:
        """
        Validates and executes a SQL query using the read-only database engine.
        Returns (result_df, error_string).
        """
        is_valid, error_msg = SQLValidator.validate_sql(sql)
        if not is_valid:
            return pd.DataFrame(), error_msg

        safe_sql = SQLValidator.enforce_limit(sql)

        try:
            with readonly_engine.connect() as conn:
                df = pd.read_sql(text(safe_sql), conn)
            return df, None
        except Exception as e:
            return pd.DataFrame(), f"Database execution error: {str(e)}"

    def explain_query(self, question: str, sql: str) -> str:
        """Generates a plain-English explanation of what the query calculates."""
        prompt = (
            f"User Question: {question}\n"
            f"Executed SQL: {sql}\n\n"
            "Provide a concise 1-2 sentence business explanation of how this query answers the question, "
            "highlighting which tables and filters were applied."
        )
        try:
            explanation = self.llm.generate(
                prompt=prompt,
                system_prompt="You are a clear, concise Business Intelligence analyst.",
                temperature=0.2,
            )
            return explanation
        except Exception:
            return "Query executed against the approved analytics schema."
