# Customer Analytics & RFM Segmentation

## 1. Natural Customer Entity Definition
In the Olist data architecture:
- `customer_id` is an order-level proxy (generated per transaction, 99,441 unique rows).
- `customer_unique_id` represents the true natural person (96,096 unique individuals).
- Always aggregate on `customer_unique_id` to evaluate:
  - Total unique customer count.
  - Customer lifetime value (LTV).
  - Repeat purchase behavior.
  - Recency, Frequency, Monetary (RFM) segmentation.

## 2. RFM Segmentation Model
InsightIQ segments the customer base using operational transaction history (relative to benchmark date 2018-10-18):
- **Champions (0.8% of base, ~123k spend):** Multiple orders, total spend $\ge$ R$ 500, purchased within the last 180 days.
- **Loyal Customers (2.5% of base, ~386k spend):** Multiple orders, purchased within the last 270 days.
- **High-Value Recent (11.1% of base, ~1.71M spend):** Single high-ticket purchase ($\ge$ R$ 300) within the last 180 days.
- **Recent One-Offs (17.0% of base, ~2.63M spend):** Single order placed within the last 180 days.
- **At Risk Repeaters (2.5% of base, ~392k spend):** Repeat buyers who haven't ordered in $> 270$ days.
- **Hibernating / One-Offs (66.1% of base, ~10.19M spend):** Single-order historical buyers inactive for $> 180$ days.

## 3. Customer Retention Characteristics
- Overall repeat purchase rate is 3.12%, typical for an e-commerce marketplace integrator where customer relationships are mediated by external host portals.
- Maximizing repeat purchase retention requires targeting High-Value Recent buyers before they cross the 180-day dormancy boundary.
