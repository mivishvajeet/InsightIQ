# Sales Analytics Business Rules & Query Guidelines

## 1. Standard Delivered Order Filter
- In standard commercial analysis, all sales, GMV, category rankings, and seller performance metrics MUST filter for completed orders: `order_status = 'delivered'` (or `is_delivered = TRUE`).
- Unfulfilled statuses (`canceled`, `unavailable`, `created`, `processing`, `invoiced`, `shipped`) must only be included when explicitly analyzing the fulfillment pipeline or cancellation rates.

## 2. Preventing Multi-Table Join Fan-Out
- An order can contain multiple line items (`order_items`, up to 21 items) and multiple payment records (`order_payments`, up to 29 payment splits).
- **Rule:** Never execute `FROM fact_order_items JOIN fact_payments ON order_id`.
- **Best Practice:** When computing revenue by order or date, query `analytics.fact_orders` or `analytics.v_monthly_sales`. When computing revenue by category or seller, query `analytics.fact_order_items` joined to `analytics.dim_products` and `analytics.fact_orders`.

## 3. Product Category Language Handling
- Product categories were originally recorded in Portuguese (`product_category_name_pt`).
- Analytical tables (`dim_products`, `v_category_performance`) provide `product_category_name_english`.
- Unmapped Portuguese categories (`pc_gamer`, `portateis_cozinha_e_preparadores_de_alimentos`) are mapped into English, and null categories are mapped to `'unknown'`.
- Analytical queries should prefer `product_category_name_english`.

## 4. Brazilian Currency & Monetary Format
- All financial metrics are denominated in Brazilian Real (BRL / R$).
- Query results should round financial figures to 2 decimal places using `ROUND(..., 2)`.
