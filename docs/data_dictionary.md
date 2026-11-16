# InsightIQ Data Dictionary

## Brazilian E-Commerce Public Dataset by Olist

This data dictionary documents the raw relational dataset used by InsightIQ, detailing table grains, primary keys, foreign key relationships, column data types, missing value percentages, and schema constraints.

---

### Table Inventory Summary

| Table Identifier | File Name | Rows | Columns | Primary Key Candidate | Grain |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `raw_orders` | `olist_orders_dataset.csv` | 99,441 | 8 | `order_id` | 1 row per customer order placement |
| `raw_order_items` | `olist_order_items_dataset.csv` | 112,650 | 7 | `(order_id, order_item_id)` | 1 row per item within an order |
| `raw_customers` | `olist_customers_dataset.csv` | 99,441 | 5 | `customer_id` | 1 row per order-specific customer token |
| `raw_products` | `olist_products_dataset.csv` | 32,951 | 9 | `product_id` | 1 row per unique catalog product |
| `raw_payments` | `olist_order_payments_dataset.csv` | 103,886 | 5 | `(order_id, payment_sequential)` | 1 row per payment installment/method |
| `raw_reviews` | `olist_order_reviews_dataset.csv` | 99,224 | 7 | `review_id` (contains duplicates) | 1 row per customer review submission |
| `raw_sellers` | `olist_sellers_dataset.csv` | 3,095 | 4 | `seller_id` | 1 row per merchant/seller |
| `raw_geolocation` | `olist_geolocation_dataset.csv` | 1,000,163 | 5 | Composite `(zip_code, lat, lng)` | Multiple rows per Brazilian postal code |
| `raw_category_translation` | `product_category_name_translation.csv` | 71 | 2 | `product_category_name` | 1 row per Portuguese to English mapping |

---

### 1. `raw_orders`
* **File:** `olist_orders_dataset.csv`
* **Grain:** 1 row per purchase order.
* **Primary Key:** `order_id` (Unique: 99,441 / 99,441, Nulls: 0)

| Column Name | Data Type | Nullable | Null % | Description & Business Rules |
| :--- | :--- | :--- | :--- | :--- |
| `order_id` | `VARCHAR(32)` | No | 0.00% | Unique 32-character hexadecimal order identifier. |
| `customer_id` | `VARCHAR(32)` | No | 0.00% | FK to `customers.customer_id`. Note: this is per-order token. |
| `order_status` | `VARCHAR(20)` | No | 0.00% | Order lifecycle status: `delivered`, `shipped`, `canceled`, `unavailable`, `invoiced`, `processing`, `created`, `approved`. |
| `order_purchase_timestamp` | `TIMESTAMP` | No | 0.00% | Timestamp when the customer submitted the order (2016-09-04 to 2018-10-17). |
| `order_approved_at` | `TIMESTAMP` | Yes | 0.16% | Timestamp when the payment was authorized (160 nulls). |
| `order_delivered_carrier_date` | `TIMESTAMP` | Yes | 1.79% | Timestamp when the logistics carrier picked up the package (1,783 nulls). |
| `order_delivered_customer_date`| `TIMESTAMP` | Yes | 2.98% | Actual delivery timestamp to the customer (2,965 nulls; 8 nulls even in 'delivered' status). |
| `order_estimated_delivery_date`| `TIMESTAMP` | No | 0.00% | Target delivery date communicated to the customer at checkout. |

---

### 2. `raw_order_items`
* **File:** `olist_order_items_dataset.csv`
* **Grain:** 1 row per physical item line inside an order.
* **Primary Key:** Composite `(order_id, order_item_id)` (Unique: 112,650 / 112,650, Nulls: 0)

| Column Name | Data Type | Nullable | Null % | Description & Business Rules |
| :--- | :--- | :--- | :--- | :--- |
| `order_id` | `VARCHAR(32)` | No | 0.00% | FK to `orders.order_id`. |
| `order_item_id` | `INTEGER` | No | 0.00% | Sequential 1-based line number for items within the same order (1 to 21). |
| `product_id` | `VARCHAR(32)` | No | 0.00% | FK to `products.product_id`. |
| `seller_id` | `VARCHAR(32)` | No | 0.00% | FK to `sellers.seller_id`. |
| `shipping_limit_date` | `TIMESTAMP` | No | 0.00% | Seller deadline to hand over parcel to logistics provider. |
| `price` | `NUMERIC(10,2)`| No | 0.00% | Item sale price in Brazilian Real (BRL / R$). Min: 0.85, Max: 6,735.00. |
| `freight_value` | `NUMERIC(10,2)`| No | 0.00% | Item freight / shipping cost in BRL. Min: 0.00, Max: 409.68. |

---

### 3. `raw_customers`
* **File:** `olist_customers_dataset.csv`
* **Grain:** 1 row per order placement token (`customer_id`).
* **Primary Key:** `customer_id` (Unique: 99,441 / 99,441, Nulls: 0)
* **Natural Key:** `customer_unique_id` (Unique: 96,096 distinct people)

| Column Name | Data Type | Nullable | Null % | Description & Business Rules |
| :--- | :--- | :--- | :--- | :--- |
| `customer_id` | `VARCHAR(32)` | No | 0.00% | Order-specific customer identifier. Used as 1:1 join key to `orders.customer_id`. |
| `customer_unique_id` | `VARCHAR(32)` | No | 0.00% | Unique identifier of the physical customer/person. Essential for retention, LTV, and repeat purchase analysis. |
| `customer_zip_code_prefix`| `VARCHAR(5)` | No | 0.00% | Five-digit postal code prefix of customer's registered location. |
| `customer_city` | `VARCHAR(50)` | No | 0.00% | Customer city name. |
| `customer_state` | `VARCHAR(2)` | No | 0.00% | Brazilian state federation code (e.g., SP, RJ, MG, RS, PR). |

---

### 4. `raw_products`
* **File:** `olist_products_dataset.csv`
* **Grain:** 1 row per catalog product.
* **Primary Key:** `product_id` (Unique: 32,951 / 32,951, Nulls: 0)

| Column Name | Data Type | Nullable | Null % | Description & Business Rules |
| :--- | :--- | :--- | :--- | :--- |
| `product_id` | `VARCHAR(32)` | No | 0.00% | Unique catalog product identifier. |
| `product_category_name` | `VARCHAR(50)` | Yes | 1.85% | Portuguese category name (610 nulls). |
| `product_name_length` | `INTEGER` | Yes | 1.85% | Number of characters in the product title. |
| `product_description_length`| `INTEGER` | Yes | 1.85% | Number of characters in the product description. |
| `product_photos_qty` | `INTEGER` | Yes | 1.85% | Number of product photos published in listing. |
| `product_weight_g` | `NUMERIC(10,2)`| Yes | 0.01% | Weight in grams (2 nulls). |
| `product_length_cm` | `NUMERIC(10,2)`| Yes | 0.01% | Length in centimeters (2 nulls). |
| `product_height_cm` | `NUMERIC(10,2)`| Yes | 0.01% | Height in centimeters (2 nulls). |
| `product_width_cm` | `NUMERIC(10,2)`| Yes | 0.01% | Width in centimeters (2 nulls). |

---

### 5. `raw_payments`
* **File:** `olist_order_payments_dataset.csv`
* **Grain:** 1 row per payment transaction installment or payment method slice.
* **Primary Key:** Composite `(order_id, payment_sequential)`

| Column Name | Data Type | Nullable | Null % | Description & Business Rules |
| :--- | :--- | :--- | :--- | :--- |
| `order_id` | `VARCHAR(32)` | No | 0.00% | FK to `orders.order_id`. |
| `payment_sequential` | `INTEGER` | No | 0.00% | Sequence index for split payments on the same order (1 to 29). |
| `payment_type` | `VARCHAR(20)` | No | 0.00% | Payment method: `credit_card`, `boleto`, `voucher`, `debit_card`, `not_defined`. |
| `payment_installments` | `INTEGER` | No | 0.00% | Number of installments selected by the customer (0 to 24). |
| `payment_value` | `NUMERIC(10,2)`| No | 0.00% | Total amount billed in this payment line (BRL). |

---

### 6. `raw_reviews`
* **File:** `olist_order_reviews_dataset.csv`
* **Grain:** 1 row per customer review attempt.
* **Primary Key:** Deduplicated on `(review_id, order_id)` or latest `review_answer_timestamp`.

| Column Name | Data Type | Nullable | Null % | Description & Business Rules |
| :--- | :--- | :--- | :--- | :--- |
| `review_id` | `VARCHAR(32)` | No | 0.00% | Identifier of the review (98,410 unique across 99,224 rows). |
| `order_id` | `VARCHAR(32)` | No | 0.00% | FK to `orders.order_id` (98,673 unique orders; 547 multi-review orders). |
| `review_score` | `INTEGER` | No | 0.00% | Customer satisfaction rating on a 1 to 5 scale. |
| `review_comment_title` | `TEXT` | Yes | 88.34% | Short review headline (optional). |
| `review_comment_message`| `TEXT` | Yes | 58.70% | Detailed customer review feedback text (optional). |
| `review_creation_date` | `TIMESTAMP` | No | 0.00% | Date when survey was sent to customer. |
| `review_answer_timestamp`| `TIMESTAMP` | No | 0.00% | Timestamp when customer submitted their rating. |

---

### 7. `raw_sellers`
* **File:** `olist_sellers_dataset.csv`
* **Grain:** 1 row per marketplace seller.
* **Primary Key:** `seller_id` (Unique: 3,095 / 3,095, Nulls: 0)

| Column Name | Data Type | Nullable | Null % | Description |
| :--- | :--- | :--- | :--- | :--- |
| `seller_id` | `VARCHAR(32)` | No | 0.00% | Unique merchant identifier. |
| `seller_zip_code_prefix`| `VARCHAR(5)` | No | 0.00% | Seller five-digit postal code. |
| `seller_city` | `VARCHAR(50)` | No | 0.00% | Seller city. |
| `seller_state` | `VARCHAR(2)` | No | 0.00% | Seller state federation code. |

---

### 8. `raw_geolocation`
* **File:** `olist_geolocation_dataset.csv`
* **Grain:** Multiple coordinate entries per postal code.
* **Rows:** 1,000,163. Staging will aggregate by `geolocation_zip_code_prefix` taking median coordinates to form `dim_geolocation`.

---

### 9. `raw_category_translation`
* **File:** `product_category_name_translation.csv`
* **Grain:** 1 row per mapped category.
* **Rows:** 71 rows. Translates Portuguese names to English. Unmapped categories fall back to clean title-case Portuguese or `'uncategorized'`.
