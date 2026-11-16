-- ====================================================================
-- InsightIQ Reusable Queries: Customer Analytics
-- ====================================================================

-- 1. How many customers made repeat purchases?
WITH customer_order_counts AS (
    SELECT 
        dc.customer_unique_id,
        COUNT(DISTINCT fo.order_id) AS order_count,
        ROUND(SUM(fo.total_order_amount), 2) AS total_spend
    FROM analytics.fact_orders fo
    JOIN analytics.dim_customers dc ON fo.customer_id = dc.customer_id
    GROUP BY dc.customer_unique_id
)
SELECT
    COUNT(*) AS total_unique_customers,
    COUNT(CASE WHEN order_count > 1 THEN 1 END) AS repeat_customers_count,
    ROUND(
        COUNT(CASE WHEN order_count > 1 THEN 1 END)::NUMERIC / 
        COUNT(*)::NUMERIC * 100.0, 
        2
    ) AS repeat_purchase_rate_pct
FROM customer_order_counts;

-- 2. Identify top high-value customers (LTV)
SELECT
    dc.customer_unique_id,
    MAX(dc.customer_city) AS city,
    MAX(dc.customer_state) AS state,
    COUNT(DISTINCT fo.order_id) AS order_count,
    ROUND(SUM(fo.total_order_amount), 2) AS total_spend_brl,
    ROUND(AVG(fo.total_order_amount), 2) AS avg_spend_per_order
FROM analytics.fact_orders fo
JOIN analytics.dim_customers dc ON fo.customer_id = dc.customer_id
WHERE fo.is_delivered = TRUE
GROUP BY dc.customer_unique_id
ORDER BY total_spend_brl DESC
LIMIT 15;

-- 3. Customer RFM segment breakdown
SELECT
    customer_segment,
    COUNT(*) AS customer_count,
    ROUND(COUNT(*)::NUMERIC / (SELECT COUNT(*) FROM analytics.v_customer_rfm_segments)::NUMERIC * 100.0, 2) AS pct_of_customers,
    ROUND(SUM(monetary), 2) AS total_revenue,
    ROUND(AVG(monetary), 2) AS avg_monetary_per_customer,
    ROUND(AVG(frequency), 2) AS avg_frequency
FROM analytics.v_customer_rfm_segments
GROUP BY customer_segment
ORDER BY total_revenue DESC;
