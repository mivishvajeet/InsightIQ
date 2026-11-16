# Review Analysis & Customer Satisfaction Drivers

## 1. Customer Satisfaction Scale
- Reviews are measured on a 1 to 5 integer Likert scale.
- Platform mean review rating is 4.09 ★ across all delivered orders.

## 2. Review Deduplication Rules
- 547 orders received multiple reviews (up to 3 submissions per order).
- `staging.stg_reviews` and `analytics.fact_orders` prioritize the latest review response by `review_answer_timestamp` via `is_latest_review_for_order = TRUE`.

## 3. Key Satisfaction Findings
- **Impact of Delivery Delays:** Orders delivered on-time average 4.29 ★. Delayed orders experience a severe drop to 2.56 ★, with 46.2% of delayed orders receiving a 1-star rating (7x higher than on-time orders).
- **Correlation vs. Causation Rule:** Delivery delay is strongly correlated with negative reviews, but the AI agent must never present an unverified hypothesis as an established sole root cause. Merchandise quality, seller accuracy, and package damage also impact ratings.
