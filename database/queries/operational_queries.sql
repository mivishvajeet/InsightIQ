-- ====================================================================
-- InsightIQ Reusable Queries: Operational Analytics
-- ====================================================================

-- 1. Which sellers have the highest cancellation rates? (Min 20 assigned orders)
SELECT
    ds.seller_id,
    ds.seller_city,
    ds.seller_state,
    sp.total_orders,
    sp.cancellation_rate_pct,
    sp.total_sales_value,
    sp.avg_review_score
FROM analytics.v_seller_performance sp
JOIN analytics.dim_sellers ds ON sp.seller_id = ds.seller_id
WHERE sp.total_orders >= 20
ORDER BY sp.cancellation_rate_pct DESC
LIMIT 10;

-- 2. Are delivery delays associated with lower customer review scores?
SELECT
    CASE
        WHEN fo.delivery_delay_days IS NULL THEN 'No Delivery Date'
        WHEN fo.delivery_delay_days <= 0 THEN 'On-Time / Early'
        WHEN fo.delivery_delay_days BETWEEN 1 AND 3 THEN 'Delayed (1-3 days)'
        WHEN fo.delivery_delay_days BETWEEN 4 AND 7 THEN 'Delayed (4-7 days)'
        ELSE 'Severely Delayed (> 7 days)'
    END AS delay_category,
    COUNT(fo.order_id) AS order_count,
    ROUND(AVG(fo.latest_review_score), 2) AS avg_review_score,
    ROUND(COUNT(CASE WHEN fo.latest_review_score <= 2 THEN 1 END)::NUMERIC / COUNT(fo.order_id)::NUMERIC * 100.0, 2) AS bad_review_pct
FROM analytics.fact_orders fo
WHERE fo.is_delivered = TRUE AND fo.latest_review_score IS NOT NULL
GROUP BY delay_category
ORDER BY avg_review_score DESC;

-- 3. Which product categories have the longest delivery lead times? (Min 100 items)
SELECT
    dp.product_category_name_english AS product_category,
    COUNT(foi.order_item_id) AS items_sold,
    ROUND(AVG(fo.delivery_lead_time_days), 2) AS avg_delivery_days,
    ROUND(AVG(fo.delivery_delay_days), 2) AS avg_delay_days,
    ROUND(AVG(fo.latest_review_score), 2) AS avg_review_score
FROM analytics.fact_order_items foi
JOIN analytics.dim_products dp ON foi.product_id = dp.product_id
JOIN analytics.fact_orders fo ON foi.order_id = fo.order_id
WHERE fo.is_delivered = TRUE AND fo.delivery_lead_time_days IS NOT NULL
GROUP BY dp.product_category_name_english
HAVING COUNT(foi.order_item_id) >= 100
ORDER BY avg_delivery_days DESC
LIMIT 10;
