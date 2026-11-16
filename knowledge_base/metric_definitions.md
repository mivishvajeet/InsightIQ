# Business Metric & KPI Definitions

## 1. Gross Merchandise Value (GMV)
- **Definition:** Total monetary value of items sold across completed delivered orders, excluding freight charges.
- **SQL Logic:** `SUM(total_item_value)` FROM `analytics.fact_orders` WHERE `is_delivered = TRUE`.
- **Verified Value:** R$ 13,221,498.11.

## 2. Total Delivered Revenue
- **Definition:** Total customer expenditure for delivered orders, including product price and shipping fees.
- **Formula:** $\text{GMV} + \text{Delivered Freight Value}$.
- **SQL Logic:** `SUM(total_order_amount)` FROM `analytics.fact_orders` WHERE `is_delivered = TRUE`.
- **Verified Value:** R$ 15,424,463.65 across 96,478 delivered orders.

## 3. Average Order Value (AOV)
- **Definition:** Mean delivered spend per unique order.
- **Formula:** $\frac{\text{Total Delivered Revenue}}{\text{Delivered Orders Count}}$.
- **Verified Value:** R$ 159.88.

## 4. Unique Customers vs Repeat Buyers
- **Total Unique Customers:** 96,096 distinct people identified via `customer_unique_id`.
- **Repeat Customers:** Customers who completed $\ge 2$ distinct orders across history (2,997 customers).
- **Repeat Purchase Rate:** $\frac{2,997}{96,096} = 3.12\%$.
- **Warning:** Never count `DISTINCT customer_id`, which is a per-order token (99,441 rows).

## 5. Delivery Performance Metrics
- **Delivery Lead Time:** Days from purchase date to actual customer doorstep delivery date. Mean: 12.6 days.
- **Delivery Delay:** Discrepancy in days between actual delivery date and estimated delivery date.
  - On-Time: $\text{Actual} \le \text{Estimated}$ (Delay $\le 0$). Platform On-Time Rate: 91.89%.
  - Delayed: $\text{Actual} > \text{Estimated}$ (Delay $> 0$).
- **Customer Satisfaction Impact:** On-time orders average 4.29 ★; delayed orders drop to 2.56 ★ (a 7x increase in 1-star reviews).

