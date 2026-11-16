-- ====================================================================
-- InsightIQ Dimensional Mart: Fact Tables
-- ====================================================================

CREATE SCHEMA IF NOT EXISTS analytics;

-- 1. Fact: Orders (Grain: 1 row per order with pre-aggregated line items and payment totals)
DROP TABLE IF EXISTS analytics.fact_orders CASCADE;
CREATE TABLE analytics.fact_orders AS
WITH order_item_aggregates AS (
    SELECT
        order_id,
        COUNT(order_item_id) AS item_count,
        COUNT(DISTINCT product_id) AS distinct_products_count,
        COUNT(DISTINCT seller_id) AS distinct_sellers_count,
        ROUND(COALESCE(SUM(price), 0), 2) AS total_item_value,
        ROUND(COALESCE(SUM(freight_value), 0), 2) AS total_freight_value,
        ROUND(COALESCE(SUM(price + freight_value), 0), 2) AS total_order_amount
    FROM staging.stg_order_items
    GROUP BY order_id
),
order_payment_aggregates AS (
    SELECT
        order_id,
        COUNT(payment_sequential) AS payment_count,
        ROUND(COALESCE(SUM(payment_value), 0), 2) AS total_payment_value,
        -- Primary payment type (by highest value)
        MODE() WITHIN GROUP (ORDER BY payment_type) AS primary_payment_type
    FROM staging.stg_payments
    GROUP BY order_id
),
order_review_aggregates AS (
    SELECT
        order_id,
        review_score AS latest_review_score,
        has_comment_message
    FROM staging.stg_reviews
    WHERE is_latest_review_for_order = TRUE
)
SELECT
    o.order_id,
    o.customer_id,
    o.order_status,
    o.order_purchase_timestamp,
    o.order_delivered_customer_date,
    o.order_estimated_delivery_date,
    o.purchase_date_key,
    o.delivered_date_key,
    o.estimated_date_key,
    o.delivery_lead_time_days,
    o.delivery_delay_days,
    o.is_on_time,
    o.is_delivered,
    COALESCE(i.item_count, 0) AS item_count,
    COALESCE(i.distinct_products_count, 0) AS distinct_products_count,
    COALESCE(i.distinct_sellers_count, 0) AS distinct_sellers_count,
    COALESCE(i.total_item_value, 0.00) AS total_item_value,
    COALESCE(i.total_freight_value, 0.00) AS total_freight_value,
    COALESCE(i.total_order_amount, 0.00) AS total_order_amount,
    COALESCE(p.payment_count, 0) AS payment_count,
    COALESCE(p.total_payment_value, 0.00) AS total_payment_value,
    COALESCE(p.primary_payment_type, 'unknown') AS primary_payment_type,
    r.latest_review_score,
    COALESCE(r.has_comment_message, FALSE) AS has_review_comment
FROM staging.stg_orders o
LEFT JOIN order_item_aggregates i ON o.order_id = i.order_id
LEFT JOIN order_payment_aggregates p ON o.order_id = p.order_id
LEFT JOIN order_review_aggregates r ON o.order_id = r.order_id;

ALTER TABLE analytics.fact_orders ADD PRIMARY KEY (order_id);
ALTER TABLE analytics.fact_orders ADD CONSTRAINT fk_fact_orders_customer FOREIGN KEY (customer_id) REFERENCES analytics.dim_customers(customer_id);
ALTER TABLE analytics.fact_orders ADD CONSTRAINT fk_fact_orders_date FOREIGN KEY (purchase_date_key) REFERENCES analytics.dim_date(date_key);

CREATE INDEX idx_fact_orders_status ON analytics.fact_orders(order_status);
CREATE INDEX idx_fact_orders_delivered ON analytics.fact_orders(is_delivered);
CREATE INDEX idx_fact_orders_purchase_date ON analytics.fact_orders(purchase_date_key);
CREATE INDEX idx_fact_orders_customer ON analytics.fact_orders(customer_id);

-- 2. Fact: Order Items (Grain: 1 row per ordered item line)
DROP TABLE IF EXISTS analytics.fact_order_items CASCADE;
CREATE TABLE analytics.fact_order_items AS
SELECT
    i.order_id,
    i.order_item_id,
    o.purchase_date_key,
    o.customer_id,
    i.product_id,
    i.seller_id,
    o.order_status,
    o.is_delivered,
    i.price,
    i.freight_value,
    i.total_item_cost,
    i.shipping_limit_date
FROM staging.stg_order_items i
JOIN staging.stg_orders o ON i.order_id = o.order_id;

ALTER TABLE analytics.fact_order_items ADD PRIMARY KEY (order_id, order_item_id);
ALTER TABLE analytics.fact_order_items ADD CONSTRAINT fk_fact_items_order FOREIGN KEY (order_id) REFERENCES analytics.fact_orders(order_id);
ALTER TABLE analytics.fact_order_items ADD CONSTRAINT fk_fact_items_product FOREIGN KEY (product_id) REFERENCES analytics.dim_products(product_id);
ALTER TABLE analytics.fact_order_items ADD CONSTRAINT fk_fact_items_seller FOREIGN KEY (seller_id) REFERENCES analytics.dim_sellers(seller_id);
ALTER TABLE analytics.fact_order_items ADD CONSTRAINT fk_fact_items_date FOREIGN KEY (purchase_date_key) REFERENCES analytics.dim_date(date_key);

CREATE INDEX idx_fact_items_prod ON analytics.fact_order_items(product_id);
CREATE INDEX idx_fact_items_seller ON analytics.fact_order_items(seller_id);
CREATE INDEX idx_fact_items_order ON analytics.fact_order_items(order_id);
CREATE INDEX idx_fact_items_delivered ON analytics.fact_order_items(is_delivered);

-- 3. Fact: Payments (Grain: 1 row per payment slice)
DROP TABLE IF EXISTS analytics.fact_payments CASCADE;
CREATE TABLE analytics.fact_payments AS
SELECT
    p.order_id,
    p.payment_sequential,
    o.purchase_date_key,
    o.customer_id,
    o.order_status,
    o.is_delivered,
    p.payment_type,
    p.payment_installments,
    p.payment_value
FROM staging.stg_payments p
JOIN staging.stg_orders o ON p.order_id = o.order_id;

ALTER TABLE analytics.fact_payments ADD PRIMARY KEY (order_id, payment_sequential);
ALTER TABLE analytics.fact_payments ADD CONSTRAINT fk_fact_pay_order FOREIGN KEY (order_id) REFERENCES analytics.fact_orders(order_id);

CREATE INDEX idx_fact_pay_order ON analytics.fact_payments(order_id);
CREATE INDEX idx_fact_pay_type ON analytics.fact_payments(payment_type);

-- 4. Fact: Reviews (Grain: 1 row per review submission)
DROP TABLE IF EXISTS analytics.fact_reviews CASCADE;
CREATE TABLE analytics.fact_reviews AS
SELECT
    r.review_id,
    r.order_id,
    o.customer_id,
    o.purchase_date_key,
    o.order_status,
    o.is_delivered,
    r.review_score,
    r.review_comment_title,
    r.review_comment_message,
    r.has_comment_message,
    r.review_creation_date,
    r.review_answer_timestamp,
    r.is_latest_review_for_order
FROM staging.stg_reviews r
JOIN staging.stg_orders o ON r.order_id = o.order_id;

ALTER TABLE analytics.fact_reviews ADD CONSTRAINT fk_fact_rev_order FOREIGN KEY (order_id) REFERENCES analytics.fact_orders(order_id);
CREATE INDEX idx_fact_rev_order ON analytics.fact_reviews(order_id);
CREATE INDEX idx_fact_rev_score ON analytics.fact_reviews(review_score);

