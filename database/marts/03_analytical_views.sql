-- ====================================================================
-- InsightIQ Analytical Views: Approved Business Intelligence Layer
-- ====================================================================

CREATE SCHEMA IF NOT EXISTS analytics;

-- 1. View: Monthly Sales Summary
DROP VIEW IF EXISTS analytics.v_monthly_sales CASCADE;
CREATE OR REPLACE VIEW analytics.v_monthly_sales AS
SELECT
    d.year_month,
    d.year,
    d.month,
    COUNT(DISTINCT fo.order_id) AS total_orders,
    COUNT(DISTINCT CASE WHEN fo.is_delivered THEN fo.order_id END) AS delivered_orders,
    ROUND(SUM(CASE WHEN fo.is_delivered THEN fo.total_item_value ELSE 0 END), 2) AS gmv,
    ROUND(SUM(CASE WHEN fo.is_delivered THEN fo.total_freight_value ELSE 0 END), 2) AS freight_revenue,
    ROUND(SUM(CASE WHEN fo.is_delivered THEN fo.total_order_amount ELSE 0 END), 2) AS total_delivered_revenue,
    ROUND(
        COALESCE(
            SUM(CASE WHEN fo.is_delivered THEN fo.total_order_amount ELSE 0 END) / 
            NULLIF(COUNT(DISTINCT CASE WHEN fo.is_delivered THEN fo.order_id END), 0),
            0
        ), 
        2
    ) AS aov,
    COUNT(DISTINCT dc.customer_unique_id) AS active_unique_customers
FROM analytics.fact_orders fo
JOIN analytics.dim_date d ON fo.purchase_date_key = d.date_key
JOIN analytics.dim_customers dc ON fo.customer_id = dc.customer_id
GROUP BY d.year_month, d.year, d.month
ORDER BY d.year_month;

-- 2. View: Category Sales Performance
DROP VIEW IF EXISTS analytics.v_category_performance CASCADE;
CREATE OR REPLACE VIEW analytics.v_category_performance AS
SELECT
    dp.product_category_name_english AS product_category,
    COUNT(foi.order_item_id) AS total_items_sold,
    COUNT(DISTINCT foi.order_id) AS total_orders,
    ROUND(SUM(foi.price), 2) AS total_revenue,
    ROUND(AVG(foi.price), 2) AS avg_item_price,
    ROUND(AVG(foi.freight_value), 2) AS avg_freight_value,
    ROUND(AVG(fo.latest_review_score), 2) AS avg_review_score
FROM analytics.fact_order_items foi
JOIN analytics.dim_products dp ON foi.product_id = dp.product_id
JOIN analytics.fact_orders fo ON foi.order_id = fo.order_id
WHERE fo.is_delivered = TRUE
GROUP BY dp.product_category_name_english
ORDER BY total_revenue DESC;

-- 3. View: State-wise Sales & Logistics Performance
DROP VIEW IF EXISTS analytics.v_state_sales_distribution CASCADE;
CREATE OR REPLACE VIEW analytics.v_state_sales_distribution AS
SELECT
    dc.customer_state,
    COUNT(DISTINCT dc.customer_unique_id) AS unique_customers,
    COUNT(DISTINCT fo.order_id) AS total_orders,
    ROUND(SUM(CASE WHEN fo.is_delivered THEN fo.total_order_amount ELSE 0 END), 2) AS total_delivered_revenue,
    ROUND(
        COALESCE(
            SUM(CASE WHEN fo.is_delivered THEN fo.total_order_amount ELSE 0 END) / 
            NULLIF(COUNT(DISTINCT CASE WHEN fo.is_delivered THEN fo.order_id END), 0),
            0
        ), 
        2
    ) AS avg_order_value,
    ROUND(AVG(CASE WHEN fo.is_delivered THEN fo.delivery_lead_time_days END), 2) AS avg_delivery_lead_time_days,
    ROUND(
        COUNT(CASE WHEN fo.is_delivered AND fo.is_on_time = TRUE THEN 1 END)::NUMERIC / 
        NULLIF(COUNT(CASE WHEN fo.is_delivered AND fo.delivery_delay_days IS NOT NULL THEN 1 END), 0)::NUMERIC * 100.0,
        2
    ) AS on_time_delivery_rate_pct
FROM analytics.dim_customers dc
JOIN analytics.fact_orders fo ON dc.customer_id = fo.customer_id
GROUP BY dc.customer_state
ORDER BY total_delivered_revenue DESC;

-- 4. View: Customer RFM Segmentation
DROP VIEW IF EXISTS analytics.v_customer_rfm_segments CASCADE;
CREATE OR REPLACE VIEW analytics.v_customer_rfm_segments AS
WITH customer_orders AS (
    SELECT
        dc.customer_unique_id,
        MAX(fo.order_purchase_timestamp) AS last_purchase_timestamp,
        COUNT(DISTINCT fo.order_id) AS total_orders,
        ROUND(SUM(CASE WHEN fo.is_delivered THEN fo.total_order_amount ELSE 0 END), 2) AS total_spend
    FROM analytics.dim_customers dc
    JOIN analytics.fact_orders fo ON dc.customer_id = fo.customer_id
    GROUP BY dc.customer_unique_id
),
rfm_raw AS (
    SELECT
        customer_unique_id,
        total_orders,
        total_spend,
        last_purchase_timestamp,
        -- Reference date: 2018-10-18 (day after dataset ends)
        EXTRACT(DAY FROM ('2018-10-18'::TIMESTAMP - last_purchase_timestamp))::INTEGER AS recency_days
    FROM customer_orders
)
SELECT
    customer_unique_id,
    recency_days,
    total_orders AS frequency,
    total_spend AS monetary,
    CASE
        WHEN total_orders > 1 AND total_spend >= 500 AND recency_days <= 180 THEN 'Champions'
        WHEN total_orders > 1 AND recency_days <= 270 THEN 'Loyal Customers'
        WHEN total_orders = 1 AND total_spend >= 300 AND recency_days <= 180 THEN 'High-Value Recent'
        WHEN total_orders = 1 AND recency_days <= 180 THEN 'Recent One-Offs'
        WHEN total_orders > 1 AND recency_days > 270 THEN 'At Risk Repeaters'
        ELSE 'Hibernating / One-Offs'
    END AS customer_segment
FROM rfm_raw;

-- 5. View: Seller Performance Summary
DROP VIEW IF EXISTS analytics.v_seller_performance CASCADE;
CREATE OR REPLACE VIEW analytics.v_seller_performance AS
SELECT
    ds.seller_id,
    ds.seller_city,
    ds.seller_state,
    COUNT(foi.order_item_id) AS total_items_sold,
    COUNT(DISTINCT foi.order_id) AS total_orders,
    ROUND(SUM(foi.price), 2) AS total_sales_value,
    ROUND(
        COUNT(CASE WHEN fo.order_status = 'canceled' THEN 1 END)::NUMERIC / 
        NULLIF(COUNT(DISTINCT fo.order_id), 0)::NUMERIC * 100.0, 
        2
    ) AS cancellation_rate_pct,
    ROUND(AVG(fo.latest_review_score), 2) AS avg_review_score
FROM analytics.dim_sellers ds
JOIN analytics.fact_order_items foi ON ds.seller_id = foi.seller_id
JOIN analytics.fact_orders fo ON foi.order_id = fo.order_id
GROUP BY ds.seller_id, ds.seller_city, ds.seller_state;

-- 6. Grant Permissions to the Read-Only Role
GRANT USAGE ON SCHEMA analytics TO insightiq_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA analytics TO insightiq_readonly;
GRANT SELECT ON ALL SEQUENCES IN SCHEMA analytics TO insightiq_readonly;
