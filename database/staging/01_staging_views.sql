-- ====================================================================
-- InsightIQ Staging Layer: Data Cleansing, Normalization & Transformations
-- ====================================================================

CREATE SCHEMA IF NOT EXISTS staging;

-- 1. Staging Customers
DROP VIEW IF EXISTS staging.stg_customers CASCADE;
CREATE OR REPLACE VIEW staging.stg_customers AS
SELECT
    customer_id,
    customer_unique_id,
    customer_zip_code_prefix,
    INITCAP(TRIM(customer_city)) AS customer_city,
    UPPER(TRIM(customer_state)) AS customer_state
FROM raw.customers;

-- 2. Staging Orders
DROP VIEW IF EXISTS staging.stg_orders CASCADE;
CREATE OR REPLACE VIEW staging.stg_orders AS
SELECT
    order_id,
    customer_id,
    LOWER(TRIM(order_status)) AS order_status,
    order_purchase_timestamp,
    order_approved_at,
    order_delivered_carrier_date,
    order_delivered_customer_date,
    order_estimated_delivery_date,
    -- Date keys for joining to dim_date
    TO_CHAR(order_purchase_timestamp, 'YYYYMMDD')::INTEGER AS purchase_date_key,
    TO_CHAR(order_delivered_customer_date, 'YYYYMMDD')::INTEGER AS delivered_date_key,
    TO_CHAR(order_estimated_delivery_date, 'YYYYMMDD')::INTEGER AS estimated_date_key,
    -- Logistics calculation: Delivery lead time in days
    CASE 
        WHEN order_delivered_customer_date IS NOT NULL 
        THEN ROUND(EXTRACT(EPOCH FROM (order_delivered_customer_date - order_purchase_timestamp)) / 86400.0, 2)
        ELSE NULL 
    END AS delivery_lead_time_days,
    -- Logistics calculation: Delivery delay in days (actual - estimated)
    CASE 
        WHEN order_delivered_customer_date IS NOT NULL 
        THEN ROUND(EXTRACT(EPOCH FROM (order_delivered_customer_date - order_estimated_delivery_date)) / 86400.0, 2)
        ELSE NULL 
    END AS delivery_delay_days,
    -- On-time delivery flag
    CASE 
        WHEN order_delivered_customer_date IS NULL THEN NULL
        WHEN order_delivered_customer_date <= order_estimated_delivery_date THEN TRUE
        ELSE FALSE 
    END AS is_on_time,
    -- Delivered status flag
    (order_status = 'delivered') AS is_delivered
FROM raw.orders;

-- 3. Staging Products with Category Translation & Fallbacks
DROP VIEW IF EXISTS staging.stg_products CASCADE;
CREATE OR REPLACE VIEW staging.stg_products AS
SELECT
    p.product_id,
    COALESCE(p.product_category_name, 'unknown') AS product_category_name_pt,
    -- Explicit category mapping for missing categories + unknown fallback
    COALESCE(
        t.product_category_name_english,
        CASE 
            WHEN p.product_category_name = 'pc_gamer' THEN 'pc_gamer'
            WHEN p.product_category_name = 'portateis_cozinha_e_preparadores_de_alimentos' THEN 'portable_kitchen_food_processors'
            WHEN p.product_category_name IS NULL THEN 'unknown'
            ELSE p.product_category_name
        END
    ) AS product_category_name_english,
    p.product_name_lenght AS product_name_length,
    p.product_description_lenght AS product_description_length,
    p.product_photos_qty,
    p.product_weight_g,
    p.product_length_cm,
    p.product_height_cm,
    p.product_width_cm,
    -- Calculated volumetric size in cubic cm
    ROUND((COALESCE(p.product_length_cm, 0) * COALESCE(p.product_height_cm, 0) * COALESCE(p.product_width_cm, 0)), 2) AS product_volume_cm3
FROM raw.products p
LEFT JOIN raw.product_category_name_translation t 
    ON p.product_category_name = t.product_category_name;

-- 4. Staging Sellers
DROP VIEW IF EXISTS staging.stg_sellers CASCADE;
CREATE OR REPLACE VIEW staging.stg_sellers AS
SELECT
    seller_id,
    seller_zip_code_prefix,
    INITCAP(TRIM(seller_city)) AS seller_city,
    UPPER(TRIM(seller_state)) AS seller_state
FROM raw.sellers;

-- 5. Staging Order Items
DROP VIEW IF EXISTS staging.stg_order_items CASCADE;
CREATE OR REPLACE VIEW staging.stg_order_items AS
SELECT
    order_id,
    order_item_id,
    product_id,
    seller_id,
    shipping_limit_date,
    price,
    freight_value,
    ROUND(price + freight_value, 2) AS total_item_cost
FROM raw.order_items;

-- 6. Staging Payments
DROP VIEW IF EXISTS staging.stg_payments CASCADE;
CREATE OR REPLACE VIEW staging.stg_payments AS
SELECT
    order_id,
    payment_sequential,
    LOWER(TRIM(payment_type)) AS payment_type,
    payment_installments,
    payment_value
FROM raw.order_payments;

-- 7. Staging Reviews with Deduplication Flag
DROP VIEW IF EXISTS staging.stg_reviews CASCADE;
CREATE OR REPLACE VIEW staging.stg_reviews AS
WITH ranked_reviews AS (
    SELECT
        review_id,
        order_id,
        review_score,
        review_comment_title,
        review_comment_message,
        review_creation_date,
        review_answer_timestamp,
        ROW_NUMBER() OVER (
            PARTITION BY order_id 
            ORDER BY review_answer_timestamp DESC, review_id DESC
        ) AS review_rank_for_order
    FROM raw.order_reviews
)
SELECT
    review_id,
    order_id,
    review_score,
    TRIM(review_comment_title) AS review_comment_title,
    TRIM(review_comment_message) AS review_comment_message,
    (review_comment_message IS NOT NULL AND LENGTH(TRIM(review_comment_message)) > 0) AS has_comment_message,
    review_creation_date,
    review_answer_timestamp,
    (review_rank_for_order = 1) AS is_latest_review_for_order
FROM ranked_reviews;

-- 8. Staging Geolocation (Aggregated by Postal Code to 1:1 Representative Coordinates)
DROP VIEW IF EXISTS staging.stg_geolocation CASCADE;
CREATE OR REPLACE VIEW staging.stg_geolocation AS
SELECT
    geolocation_zip_code_prefix AS zip_code_prefix,
    ROUND(AVG(geolocation_lat)::NUMERIC, 6) AS latitude,
    ROUND(AVG(geolocation_lng)::NUMERIC, 6) AS longitude,
    MODE() WITHIN GROUP (ORDER BY INITCAP(TRIM(geolocation_city))) AS representative_city,
    MODE() WITHIN GROUP (ORDER BY UPPER(TRIM(geolocation_state))) AS representative_state
FROM raw.geolocation
GROUP BY geolocation_zip_code_prefix;
