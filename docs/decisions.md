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

