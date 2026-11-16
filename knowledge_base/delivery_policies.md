# Delivery Policies & Fulfillment Operations

## 1. Fulfillment Milestones
Each order tracks three sequential fulfillment timestamps:
1. `order_purchase_timestamp`: Order placement by customer.
2. `order_delivered_carrier_date`: Seller handoff to postal carrier.
3. `order_delivered_customer_date`: Final doorstep delivery.
4. `order_estimated_delivery_date`: Promised delivery deadline quoted at checkout.

## 2. Delivery Lead Time Benchmarks
- Mean transit duration across Brazil is 12.6 days.
- Southern and Southeastern states (SP, RJ, MG, PR, SC) enjoy the fastest transit times (8-11 days).
- Northern and Northeastern states (RR, AP, AM, PA, BA) experience significantly longer transit durations (20-28 days) due to geographic distance and river/road transit constraints.

## 3. SLA & Cancellation Policies
- Sellers are required to dispatch orders before `shipping_limit_date`.
- Sellers exceeding a 10% cancellation threshold are flagged in `analytics.v_seller_performance` for merchant performance reviews.
