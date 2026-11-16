# Database Schema & Data Architecture

## Schema Overview
InsightIQ models Olist data in PostgreSQL using three isolated schemas:
1. `raw`: Ingested source CSV tables (raw text, timestamps, untransformed).
2. `staging`: Cleansed views with standardized text formatting, mapped categories, and deduplicated review ranks.
3. `analytics`: Dimensional star schema (facts, dimensions, and reporting views). The AI Agent has access **only** to the `analytics` schema via read-only credentials.

## Analytical Dimensional Tables (`analytics.*`)

### Dimension Tables
- **`dim_customers`**: Grain: 1 row per order customer (`customer_id`).
  - Columns: `customer_id`, `customer_unique_id`, `customer_city`, `customer_state`, `customer_zip_code_prefix`.
  - **Rule:** Retention, cohorts, and repeat buyer queries MUST group or count by `customer_unique_id`.
- **`dim_products`**: Grain: 1 row per catalog product (`product_id`).
  - Columns: `product_id`, `product_category_name_english`, `product_category_name_pt`, `product_weight_g`, `product_volume_cm3`.
- **`dim_sellers`**: Grain: 1 row per merchant (`seller_id`).
  - Columns: `seller_id`, `seller_city`, `seller_state`, `seller_zip_code_prefix`.
- **`dim_date`**: Calendar dimension table covering 2016-01-01 to 2018-12-31 (`date_key`, `full_date`, `year`, `month`, `year_month`, `day_name`).

### Fact Tables
- **`fact_orders`**: Grain: 1 row per customer order placement (`order_id`).
  - Pre-aggregated metrics: `total_item_value`, `total_freight_value`, `total_order_amount`, `item_count`, `payment_count`, `total_payment_value`, `latest_review_score`, `delivery_lead_time_days`, `delivery_delay_days`, `is_on_time`, `is_delivered`.
  - **Cardinality Warning:** Use `fact_orders` for all order-level queries (Revenue, AOV, Orders Count, Delivery Time) to prevent Cartesian duplication!
- **`fact_order_items`**: Grain: 1 row per ordered line item (`order_id`, `order_item_id`).
  - Measures: `price`, `freight_value`, `total_item_cost`.
- **`fact_payments`**: Grain: 1 row per payment slice (`order_id`, `payment_sequential`).
  - Measures: `payment_type`, `payment_installments`, `payment_value`.
- **`fact_reviews`**: Grain: 1 row per customer review submission (`review_id`).
  - Measures: `review_score` (1-5), `has_comment_message`, `is_latest_review_for_order`.

### Approved Analytical Views
- `v_monthly_sales`: Monthly revenue, orders, GMV, and AOV.
- `v_category_performance`: Product category rankings by revenue, volume, and satisfaction.
- `v_state_sales_distribution`: State-level sales, customer counts, and on-time fulfillment rates.
- `v_customer_rfm_segments`: Recency, Frequency, Monetary customer segments at `customer_unique_id` grain.
- `v_seller_performance`: Seller total sales, assigned orders, and cancellation rates.
