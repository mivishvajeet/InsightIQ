# Architecture & Data Engineering Decisions (ADR)

## Phase 1: Data Exploration, Quality Assessment, & Analytical Modeling

This document records the foundational architectural decisions taken based on empirical findings during the Phase 1 profiling of the Olist dataset.

---

### Decision 1: Avoiding Join Fan-Out and Cardinality Inflation Between Items and Payments

* **Context:**
  In the Olist dataset, both `order_items` and `order_payments` relate to `orders` via a 1:many relationship.
  - 9,803 orders (9.94%) contain multiple order items (up to 21 items in a single order).
  - 2,961 orders (2.98%) contain multiple payment methods or installments (up to 29 payment records for a single order).
* **Problem:**
  If an analytical query naively executes `JOIN order_items ON ... JOIN order_payments ON order_items.order_id = order_payments.order_id`, a Cartesian product occurs on orders with multiple items and payments. Profiling reveals that such a direct join expands 112,650 item records into 117,601 records (a 4.4% fan-out error), artificially inflating both revenue and payment sums.
* **Decision:**
  - Maintain separate fact tables: `analytics.fact_orders` (grain: 1 row per order), `analytics.fact_order_items` (grain: 1 row per order item), and `analytics.fact_payments` (grain: 1 row per payment slice).
  - Pre-aggregate item metrics (`total_item_value`, `total_freight_value`, `item_count`) and payment metrics (`total_payment_value`, `payment_count`) into `fact_orders`.
  - When querying items by category or seller together with payments, always aggregate each side separately (e.g. using CTEs or separate fact joins) before combining.

---

### Decision 2: Distinct Customer Entity Representation (`customer_id` vs `customer_unique_id`)

* **Context:**
  In `olist_customers_dataset.csv`, there are two identifier columns:
  1. `customer_id`: 99,441 unique values, strictly 1:1 with the 99,441 rows in `olist_orders_dataset.csv`.
  2. `customer_unique_id`: 96,096 unique values, representing the true physical person.
* **Problem:**
  If the AI agent or an analyst queries `COUNT(DISTINCT customer_id)` or groups by `customer_id` to compute customer retention, lifetime value (LTV), or repeat purchase rates, the repeat purchase rate would erroneously calculate to 0.00% because every order has a distinct `customer_id`.
* **Decision:**
  - `dim_customers` will explicitly store both `customer_id` and `customer_unique_id`.
  - All customer retention, cohort, repeat rate, and segmentation queries will explicitly aggregate on `customer_unique_id`.
  - The business knowledge base and RAG retrieval chunks will explicitly teach the LLM the distinction between the two identifiers.

---

### Decision 3: Handling Multiple Reviews per Order

* **Context:**
  In `olist_order_reviews_dataset.csv`, 98,673 distinct orders received reviews, but 547 orders received multiple reviews (up to 3 submissions per order), producing 99,224 total review rows.
* **Decision:**
  - In `staging.stg_reviews`, deduplicate by order using `ROW_NUMBER() OVER (PARTITION BY order_id ORDER BY review_answer_timestamp DESC, review_id DESC)` to provide a canonical 1:1 review record per order.
  - In `analytics.fact_reviews`, preserve the full review log while flagging `is_latest_review_for_order` for analytical queries that require a 1:1 join with `fact_orders`.

---

### Decision 4: Translation of Product Categories & Missing Fallbacks

* **Context:**
  `product_category_name_translation.csv` provides English translations for 71 categories. However, profiling revealed that:
  - 610 products have a null `product_category_name`.
  - 2 categories in `products` are missing from the translation file: `'pc_gamer'` and `'portateis_cozinha_e_preparadores_de_alimentos'`.
* **Decision:**
  - In `dim_products`, provide `product_category_name_english` using `COALESCE` with a mapping dictionary for missing categories:
    - `'pc_gamer'` $\rightarrow$ `'pc_gamer'` (English: PC Gamer)
    - `'portateis_cozinha_e_preparadores_de_alimentos'` $\rightarrow$ `'portable_kitchen_food_processors'`
    - Null values $\rightarrow$ `'unknown'`
  - Ensures zero orphan values when filtering or grouping by English product categories.

---

### Decision 5: Delivered Order Filter as Standard Business Baseline

* **Context:**
  Out of 99,441 orders in the dataset, 96,478 are `delivered` (97.02%). The remaining 2,963 orders are in incomplete or failed states (`shipped`, `canceled`, `unavailable`, `invoiced`, `processing`, `created`, `approved`). Moreover, 775 non-delivered orders contain no line items in `olist_order_items_dataset.csv`.
* **Decision:**
  - By default, core sales performance metrics (Revenue, GMV, AOV, Seller Sales, Category Sales) must explicitly filter for `order_status = 'delivered'` unless the user question specifically asks about cancellations, pipeline orders, or fulfillment drop-offs.
  - This rule will be codified in `metric_definitions.md`, `sales_business_rules.md`, and SQL analytics views.

---

## Phase 2: PostgreSQL Architecture, Schema Isolation, & Role-Based Security

### Decision 6: Port Isolation & Local Service Compatibility

* **Context:**
  A running Docker container (`buildlog-db`) already occupied port `5432` on the host machine.
* **Decision:**
  - Configured InsightIQ's PostgreSQL service in `docker-compose.yml` to bind to port `${POSTGRES_PORT:-5433}:5432`.
  - Kept default internal container port at 5432 with explicit environment variable mapping across `.env` and `backend/app/services/database.py`.
  - Avoided any port conflicts or interruption to existing workloads.

---

### Decision 7: Multi-Schema Isolation and Principle of Least Privilege

* **Context:**
  An autonomous AI agent generating SQL queries poses risks of accidental data modification, destructive DDL, or data exposure.
* **Decision:**
  - Segregated database into three schemas:
    1. `raw`: Ingested source tables with zero transformation.
    2. `staging`: Cleaned views and type-cast models.
    3. `analytics`: Fact tables, dimension tables, and approved business reporting views.
  - Created a dedicated `insightiq_readonly` role with:
    - `default_transaction_read_only = on`
    - `statement_timeout = '10s'`
    - Access granted **exclusively** to the `analytics` schema (`GRANT USAGE ON SCHEMA analytics`).
    - Explicit `REVOKE ALL` on `raw` and `staging`.
    - Absolute inability to run `INSERT`, `UPDATE`, `DELETE`, or `DROP`.

---

## Phase 3: Dimensional Modeling, Staging Transforms, & Analytics Marts

### Decision 8: Pre-Aggregated Metrics in `fact_orders` for Fast, Fan-Out-Free Analytical Queries

* **Context:**
  In BI applications and LLM text-to-SQL generation, questions such as "What is the monthly revenue?", "What is the average order value?", and "Compare sales performance across Brazilian states" frequently lead to improper join cardinality errors when LLMs join orders, order_items, and payments in a single query.
* **Decision:**
  - Designed `analytics.fact_orders` with pre-aggregated order level metrics:
    - `total_item_value`, `total_freight_value`, `total_order_amount`, `item_count`, `payment_count`, `total_payment_value`, `latest_review_score`, `delivery_lead_time_days`, `delivery_delay_days`.
  - High-level KPI questions can now be answered directly from `fact_orders` without multi-table joins.
  - Granular queries (by product category or seller) query `fact_order_items` joined to `dim_products` and `dim_sellers`.

### Decision 9: RFM Customer Segmentation View

* **Context:**
  Questions regarding customer loyalty, high-value customers, and churn risk require Recency, Frequency, and Monetary (RFM) scoring.
* **Decision:**
  - Implemented `analytics.v_customer_rfm_segments` with explicit cut-offs based on the 2016-2018 dataset distribution:
    - Reference anchor date: `2018-10-18` (one day after dataset operational close).
    - Customer segments: `Champions`, `Loyal Customers`, `High-Value Recent`, `Recent One-Offs`, `At Risk Repeaters`, `Hibernating / One-Offs`.
    - Computed at the `customer_unique_id` grain.

---

## Phase 4: Python Analytical Engine & Interactive BI Dashboard

### Decision 10: Parametric & Non-Parametric Dual Anomaly Detection

* **Context:**
  Time-series revenue fluctuations in e-commerce can stem from regular promotional events or operational failures.
* **Decision:**
  - Combined parametric Z-Score ($z > 2.5$) with non-parametric IQR ($1.5 \times IQR$).
  - Identified `2017-11-24` as Black Friday ($Z = 10.44$, R\$ 175k revenue in a single day).
  - Provided contextual metadata tagging to distinguish expected marketing events from operational disruptions.

### Decision 11: Correlation vs. Causation Guardrails in Analytics Engine

* **Context:**
  Business users and agents often conflate statistical correlation with causation (e.g. asserting that slow deliveries *cause* all bad reviews, ignoring defective merchandise or uncommunicative sellers).
* **Decision:**
  - Built `CorrelationAnalyzer` calculating Pearson $r$ and Spearman $\rho$.
  - Quantified the impact: delayed orders drop from 4.29 to 2.56 average stars and increase 1-star review probability by 7.02x.
  - Mandated that the analytical tool return explicit caveat strings forbidding the agent from claiming proven causation without controlled A/B testing.

---

## Phase 5: Local LLM Integration (Ollama + Qwen 2.5 3B) & SQL Security Engine

### Decision 12: Local Ollama Runtime for Zero-Cost, Private LLM Execution

* **Context:**
  Project requirements mandate: "All core functionality must work locally without paid APIs or subscriptions. Ollama — local LLM runtime, Qwen 2.5 3B — primary LLM, Nomic Embed Text — embedding model."
* **Decision:**
  - Installed and initiated Ollama service locally (`http://localhost:11434`).
  - Pulled `qwen2.5:3b` (3.1B parameter model with tools/completion capability) and `nomic-embed-text` (768-dim embeddings).
  - Built `OllamaClient` with structured JSON mode, connection health checks, and 45s timeout protection.

### Decision 13: Few-Shot Grounding and Self-Healing SQL Reflection Loop

* **Context:**
  Small local models (3B) can occasionally make minor column naming errors on complex relational schemas (e.g., guessing `date_key` instead of `order_purchase_timestamp` or `v_monthly_sales`).
* **Decision:**
  - Enriched system prompts with concrete few-shot exemplars mapping natural language questions to approved analytics views.
  - Built `generate_and_execute` with an automated self-healing retry loop: if PostgreSQL returns a syntax or column error, the error traceback is reflected back to Qwen to self-correct in real time.
  - Enforced deterministic temperature ($T = 0.0$) for SQL generation to guarantee reproducible queries.
