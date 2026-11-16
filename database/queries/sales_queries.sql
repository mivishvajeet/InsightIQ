-- ====================================================================
-- InsightIQ Reusable Queries: Sales Analytics
-- ====================================================================

-- 1. Monthly Revenue & Sales Trend
SELECT
    year_month,
    delivered_orders,
    gmv,
    freight_revenue,
    total_delivered_revenue,
    aov,
    active_unique_customers
FROM analytics.v_monthly_sales
ORDER BY year_month;

-- 2. Which product category generates the highest sales?
SELECT
    product_category,
    total_items_sold,
    total_revenue,
    avg_item_price,
    avg_review_score
FROM analytics.v_category_performance
ORDER BY total_revenue DESC
LIMIT 10;

-- 3. Compare sales performance across Brazilian states
SELECT
    customer_state,
    unique_customers,
    total_orders,
    total_delivered_revenue,
    avg_order_value,
    avg_delivery_lead_time_days,
    on_time_delivery_rate_pct
FROM analytics.v_state_sales_distribution
ORDER BY total_delivered_revenue DESC;

-- 4. What is the average order value (AOV)?
SELECT 
    ROUND(SUM(total_order_amount) / NULLIF(COUNT(DISTINCT order_id), 0), 2) AS aov,
    ROUND(SUM(total_item_value) / NULLIF(COUNT(DISTINCT order_id), 0), 2) AS avg_item_value,
    ROUND(SUM(total_freight_value) / NULLIF(COUNT(DISTINCT order_id), 0), 2) AS avg_freight_value
FROM analytics.fact_orders
WHERE is_delivered = TRUE;

-- 5. Which month had the highest revenue?
SELECT
    year_month,
    total_delivered_revenue,
    delivered_orders,
    aov
FROM analytics.v_monthly_sales
ORDER BY total_delivered_revenue DESC
LIMIT 1;

