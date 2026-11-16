-- ====================================================================
-- InsightIQ Dimensional Mart: Dimension Tables
-- ====================================================================

CREATE SCHEMA IF NOT EXISTS analytics;

-- 1. Dimension: Date (Calendar Dimension)
DROP TABLE IF EXISTS analytics.dim_date CASCADE;
CREATE TABLE analytics.dim_date (
    date_key INTEGER PRIMARY KEY,           -- Format: YYYYMMDD
    full_date DATE NOT NULL,
    year INTEGER NOT NULL,
    quarter INTEGER NOT NULL,
    month INTEGER NOT NULL,
    month_name VARCHAR(20) NOT NULL,
    year_month VARCHAR(7) NOT NULL,         -- Format: YYYY-MM
    week_of_year INTEGER NOT NULL,
    day_of_month INTEGER NOT NULL,
    day_of_week INTEGER NOT NULL,           -- 1 = Monday, 7 = Sunday
    day_name VARCHAR(20) NOT NULL,
    is_weekend BOOLEAN NOT NULL
);

-- Populate dim_date for all dates covering Olist operational history (2016 to 2018)
INSERT INTO analytics.dim_date
SELECT
    TO_CHAR(d, 'YYYYMMDD')::INTEGER AS date_key,
    d::DATE AS full_date,
    EXTRACT(YEAR FROM d)::INTEGER AS year,
    EXTRACT(QUARTER FROM d)::INTEGER AS quarter,
    EXTRACT(MONTH FROM d)::INTEGER AS month,
    TO_CHAR(d, 'Month') AS month_name,
    TO_CHAR(d, 'YYYY-MM') AS year_month,
    EXTRACT(WEEK FROM d)::INTEGER AS week_of_year,
    EXTRACT(DAY FROM d)::INTEGER AS day_of_month,
    EXTRACT(ISODOW FROM d)::INTEGER AS day_of_week,
    TO_CHAR(d, 'Day') AS day_name,
    (EXTRACT(ISODOW FROM d) IN (6, 7)) AS is_weekend
FROM GENERATE_SERIES('2016-01-01'::DATE, '2018-12-31'::DATE, '1 day'::INTERVAL) d;

CREATE INDEX idx_dim_date_ym ON analytics.dim_date(year_month);
CREATE INDEX idx_dim_date_year ON analytics.dim_date(year);

-- 2. Dimension: Customers
DROP TABLE IF EXISTS analytics.dim_customers CASCADE;
CREATE TABLE analytics.dim_customers AS
SELECT
    customer_id,
    customer_unique_id,
    customer_zip_code_prefix,
    customer_city,
    customer_state
FROM staging.stg_customers;

ALTER TABLE analytics.dim_customers ADD PRIMARY KEY (customer_id);
CREATE INDEX idx_dim_cust_unique ON analytics.dim_customers(customer_unique_id);
CREATE INDEX idx_dim_cust_state ON analytics.dim_customers(customer_state);

-- 3. Dimension: Products
DROP TABLE IF EXISTS analytics.dim_products CASCADE;
CREATE TABLE analytics.dim_products AS
SELECT
    product_id,
    product_category_name_english,
    product_category_name_pt,
    product_name_length,
    product_description_length,
    product_photos_qty,
    product_weight_g,
    product_length_cm,
    product_height_cm,
    product_width_cm,
    product_volume_cm3
FROM staging.stg_products;

ALTER TABLE analytics.dim_products ADD PRIMARY KEY (product_id);
CREATE INDEX idx_dim_prod_cat_en ON analytics.dim_products(product_category_name_english);

-- 4. Dimension: Sellers
DROP TABLE IF EXISTS analytics.dim_sellers CASCADE;
CREATE TABLE analytics.dim_sellers AS
SELECT
    seller_id,
    seller_zip_code_prefix,
    seller_city,
    seller_state
FROM staging.stg_sellers;

ALTER TABLE analytics.dim_sellers ADD PRIMARY KEY (seller_id);
CREATE INDEX idx_dim_sellers_state ON analytics.dim_sellers(seller_state);
