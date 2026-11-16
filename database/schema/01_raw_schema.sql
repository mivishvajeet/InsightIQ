-- ====================================================================
-- InsightIQ Raw Layer DDL: Olist E-Commerce Tables
-- ====================================================================

CREATE SCHEMA IF NOT EXISTS raw;

-- 1. Raw Customers
CREATE TABLE IF NOT EXISTS raw.customers (
    customer_id VARCHAR(32) PRIMARY KEY,
    customer_unique_id VARCHAR(32) NOT NULL,
    customer_zip_code_prefix VARCHAR(10) NOT NULL,
    customer_city VARCHAR(100) NOT NULL,
    customer_state VARCHAR(5) NOT NULL
);

-- 2. Raw Orders
CREATE TABLE IF NOT EXISTS raw.orders (
    order_id VARCHAR(32) PRIMARY KEY,
    customer_id VARCHAR(32) NOT NULL REFERENCES raw.customers(customer_id),
    order_status VARCHAR(30) NOT NULL,
    order_purchase_timestamp TIMESTAMP NOT NULL,
    order_approved_at TIMESTAMP,
    order_delivered_carrier_date TIMESTAMP,
    order_delivered_customer_date TIMESTAMP,
    order_estimated_delivery_date TIMESTAMP NOT NULL
);

-- 3. Raw Products
CREATE TABLE IF NOT EXISTS raw.products (
    product_id VARCHAR(32) PRIMARY KEY,
    product_category_name VARCHAR(100),
    product_name_lenght INTEGER,
    product_description_lenght INTEGER,
    product_photos_qty INTEGER,
    product_weight_g NUMERIC(10, 2),
    product_length_cm NUMERIC(10, 2),
    product_height_cm NUMERIC(10, 2),
    product_width_cm NUMERIC(10, 2)
);

-- 4. Raw Sellers
CREATE TABLE IF NOT EXISTS raw.sellers (
    seller_id VARCHAR(32) PRIMARY KEY,
    seller_zip_code_prefix VARCHAR(10) NOT NULL,
    seller_city VARCHAR(100) NOT NULL,
    seller_state VARCHAR(5) NOT NULL
);

-- 5. Raw Order Items
CREATE TABLE IF NOT EXISTS raw.order_items (
    order_id VARCHAR(32) NOT NULL REFERENCES raw.orders(order_id),
    order_item_id INTEGER NOT NULL,
    product_id VARCHAR(32) NOT NULL REFERENCES raw.products(product_id),
    seller_id VARCHAR(32) NOT NULL REFERENCES raw.sellers(seller_id),
    shipping_limit_date TIMESTAMP NOT NULL,
    price NUMERIC(10, 2) NOT NULL,
    freight_value NUMERIC(10, 2) NOT NULL,
    PRIMARY KEY (order_id, order_item_id)
);

-- 6. Raw Payments
CREATE TABLE IF NOT EXISTS raw.order_payments (
    order_id VARCHAR(32) NOT NULL REFERENCES raw.orders(order_id),
    payment_sequential INTEGER NOT NULL,
    payment_type VARCHAR(30) NOT NULL,
    payment_installments INTEGER NOT NULL,
    payment_value NUMERIC(10, 2) NOT NULL,
    PRIMARY KEY (order_id, payment_sequential)
);

-- 7. Raw Reviews
CREATE TABLE IF NOT EXISTS raw.order_reviews (
    review_id VARCHAR(32) NOT NULL,
    order_id VARCHAR(32) NOT NULL REFERENCES raw.orders(order_id),
    review_score INTEGER NOT NULL,
    review_comment_title TEXT,
    review_comment_message TEXT,
    review_creation_date TIMESTAMP NOT NULL,
    review_answer_timestamp TIMESTAMP NOT NULL
);

-- 8. Raw Geolocation
CREATE TABLE IF NOT EXISTS raw.geolocation (
    geolocation_zip_code_prefix VARCHAR(10) NOT NULL,
    geolocation_lat NUMERIC(10, 8) NOT NULL,
    geolocation_lng NUMERIC(11, 8) NOT NULL,
    geolocation_city VARCHAR(100) NOT NULL,
    geolocation_state VARCHAR(5) NOT NULL
);

-- 9. Raw Product Category Name Translation
CREATE TABLE IF NOT EXISTS raw.product_category_name_translation (
    product_category_name VARCHAR(100) PRIMARY KEY,
    product_category_name_english VARCHAR(100) NOT NULL
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_raw_orders_customer ON raw.orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_raw_orders_status ON raw.orders(order_status);
CREATE INDEX IF NOT EXISTS idx_raw_orders_purchase ON raw.orders(order_purchase_timestamp);
CREATE INDEX IF NOT EXISTS idx_raw_order_items_product ON raw.order_items(product_id);
CREATE INDEX IF NOT EXISTS idx_raw_order_items_seller ON raw.order_items(seller_id);
CREATE INDEX IF NOT EXISTS idx_raw_order_payments_order ON raw.order_payments(order_id);
CREATE INDEX IF NOT EXISTS idx_raw_order_reviews_order ON raw.order_reviews(order_id);
CREATE INDEX IF NOT EXISTS idx_raw_geolocation_zip ON raw.geolocation(geolocation_zip_code_prefix);
