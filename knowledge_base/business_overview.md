# Business Overview: Olist E-Commerce Platform

## 1. Company Profile
Olist is a Brazilian e-commerce marketplace integrator that connects small and medium-sized merchants across Brazil to major national marketplaces (such as Mercado Livre, B2W, Amazon, Magazine Luiza). Merchants list products through Olist, and when customers make purchases on partner marketplaces, Olist routes orders to merchants for fulfillment and arranges delivery via partner logistics carriers.

## 2. Operational Dataset Scope
- **Timeframe:** September 2016 to October 2018.
- **Transactions:** 99,441 customer orders, comprising 112,650 purchased product items.
- **Customer Base:** 96,096 distinct individuals across all 27 Brazilian federal units/states.
- **Merchant Network:** 3,095 registered marketplace sellers.
- **Gross Merchandise Value:** R$ 13,221,498.11 in delivered product value (R$ 15,424,463.65 including freight).

## 3. Marketplace Flow
1. **Purchase Placement:** Customer submits order on partner marketplace. An order-specific `customer_id` is created alongside the permanent person identifier `customer_unique_id`.
2. **Payment Authorization:** Payment processed via credit card, boleto bancário, voucher, or debit card.
3. **Dispatch to Carrier:** Seller packs parcel and hands it to the logistics carrier before `shipping_limit_date`.
4. **Customer Delivery:** Carrier delivers package to customer address.
5. **Customer Feedback:** Customer receives satisfaction survey rating the order from 1 to 5 stars.

