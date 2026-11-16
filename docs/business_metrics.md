# InsightIQ Business Metrics & KPI Definitions

This document defines the official business logic, mathematical formulas, SQL implementations, and edge-case handling for all core KPIs in InsightIQ.

---

### 1. Revenue & Sales Metrics

#### Gross Merchandise Value (GMV)
* **Definition:** Total value of products sold across delivered orders, excluding shipping freight.
* **Formula:** $\sum \text{price}$ where $\text{order\_status} = \text{'delivered'}$
* **Data Source:** `analytics.fact_order_items` joined with `analytics.fact_orders`
* **Verified Dataset Value:** **R\$ 13,221,498.11**
* **SQL Implementation:**
```sql
SELECT ROUND(SUM(foi.price), 2) AS gmv
FROM analytics.fact_order_items foi
JOIN analytics.fact_orders fo ON foi.order_id = fo.order_id
WHERE fo.order_status = 'delivered';
```

#### Total Delivered Revenue (Net Merchandise + Freight)
* **Definition:** Total monetary value collected from customers for completed delivered transactions (item price plus freight charge).
* **Formula:** $\sum (\text{price} + \text{freight\_value})$ where $\text{order\_status} = \text{'delivered'}$
* **Verified Dataset Value:** **R\$ 15,424,463.65**
* **Payment Perspective Comparison:** `SUM(payment_value)` for delivered orders is **R\$ 15,422,461.77** (difference of R\$ 2,001.88 due to voucher deductions and small platform rounding).
* **SQL Implementation:**
```sql
SELECT ROUND(SUM(foi.price + foi.freight_value), 2) AS total_delivered_revenue
FROM analytics.fact_order_items foi
JOIN analytics.fact_orders fo ON foi.order_id = fo.order_id
WHERE fo.order_status = 'delivered';
```

#### Average Order Value (AOV)
* **Definition:** Average revenue generated per unique delivered order.
* **Formula:** $\frac{\text{Total Delivered Revenue}}{\text{Total Delivered Orders}}$
* **Verified Dataset Value:** $\frac{15,424,463.65}{96,478} = \text{\bf R\$ 159.88}$
* **SQL Implementation:**
```sql
SELECT ROUND(SUM(total_order_amount) / COUNT(DISTINCT order_id), 2) AS aov
FROM analytics.fact_orders
WHERE order_status = 'delivered';
```

---

### 2. Customer Analytics Metrics

#### Total Unique Customers
* **Definition:** Count of distinct real individuals who have purchased on the platform.
* **Critical Rule:** MUST count `DISTINCT customer_unique_id`, **NOT** `customer_id`. `customer_id` is an order-level proxy token (99,441 rows), whereas `customer_unique_id` identifies the actual consumer (96,096 distinct persons).
* **Verified Dataset Value:** **96,096**
* **SQL Implementation:**
```sql
SELECT COUNT(DISTINCT dc.customer_unique_id) AS unique_customers
FROM analytics.fact_orders fo
JOIN analytics.dim_customers dc ON fo.customer_id = dc.customer_id;
```

#### Repeat Purchase Rate
* **Definition:** The percentage of unique customers who placed more than one order across the platform's history.
* **Formula:** $\frac{\text{Customers with } \ge 2 \text{ Orders}}{\text{Total Unique Customers}} \times 100\%$
* **Dataset Numbers:**
  - Customers with $\ge 2$ orders: 2,997
  - Total unique customers: 96,096
  - Repeat Purchase Rate: $\frac{2,997}{96,096} = \text{\bf 3.12\%}$
* **SQL Implementation:**
```sql
WITH customer_order_counts AS (
    SELECT dc.customer_unique_id, COUNT(DISTINCT fo.order_id) AS order_count
    FROM analytics.fact_orders fo
    JOIN analytics.dim_customers dc ON fo.customer_id = dc.customer_id
    GROUP BY dc.customer_unique_id
)
SELECT 
    ROUND(
        COUNT(CASE WHEN order_count > 1 THEN 1 END)::NUMERIC / 
        COUNT(*)::NUMERIC * 100.0, 
        2
    ) AS repeat_purchase_rate_pct
FROM customer_order_counts;
```

---

### 3. Operational & Logistics Metrics

#### Delivery Lead Time (Days)
* **Definition:** Number of elapsed days between the customer purchase timestamp and the final doorstep delivery timestamp.
* **Formula:** $\text{order\_delivered\_customer\_date} - \text{order\_purchase\_timestamp}$
* **Filtering:** Evaluated solely on delivered orders where both timestamps are non-null.

#### Delivery Delay (Days)
* **Definition:** The discrepancy between actual customer delivery timestamp and estimated delivery date communicated at checkout.
* **Formula:** $\text{DATE(order\_delivered\_customer\_date)} - \text{DATE(order\_estimated\_delivery\_date)}$
* **Classification:**
  - Delayed: $\text{Actual Delivery Date} > \text{Estimated Delivery Date}$
  - On-Time / Early: $\text{Actual Delivery Date} \le \text{Estimated Delivery Date}$

#### On-Time Delivery Rate
* **Definition:** Percentage of delivered orders arrived on or before the estimated delivery date.
* **Formula:** $\frac{\text{Delivered Orders where Delay} \le 0}{\text{Total Delivered Orders with Delivery Date}} \times 100\%$

#### Seller Cancellation Rate
* **Definition:** Percentage of an individual seller's orders that were canceled.
* **Formula:** $\frac{\text{Canceled Orders for Seller}}{\text{Total Orders Assigned to Seller}} \times 100\%$

---

### 4. Customer Satisfaction Metrics

#### Average Review Score
* **Definition:** Mean rating assigned by customers on a 1 to 5 Likert scale.
* **Formula:** $\frac{\sum \text{review\_score}}{\text{Count of Reviews}}$
* **Handling Multiple Reviews:** When an order receives multiple reviews (547 occurrences), analytical views use the most recent review by `review_answer_timestamp` or average score per order.
* **Verified Dataset Value:** **4.09**

