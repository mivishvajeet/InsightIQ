# InsightIQ: Agentic Business Intelligence Platform
> AI-powered Business Intelligence platform using RAG, LLMs, and Natural Language SQL on Brazilian E-Commerce data.

---

## Architecture Overview

InsightIQ enables business users and data analysts to interact with enterprise data using natural language, backed by a production-grade analytics data warehouse, semantic RAG retrieval, and an agentic orchestrator.

```
+-------------------------------------------------------------+
|                      Streamlit Frontend                     |
|   (Executive KPIs | Sales | Customers | AI Analyst | Reports)|
+------------------------------+------------------------------+
                               | REST API
+------------------------------v------------------------------+
|                     FastAPI Backend                         |
|   - Pydantic Schema Validation & Authentication             |
|   - Multi-step Agent Orchestrator                           |
+----+-------------------+--------------------+---------------+
     |                   |                    |
+----v-----+       +-----v------+       +-----v-------+
| SQL Tool |       |  RAG Tool  |       | Python Tool |
| (Postgres|       | (ChromaDB +|       | (Pandas /   |
| Read-Only|       |  Nomic)    |       |  Stats)     |
+----+-----+       +------------+       +-------------+
     |
+----v--------------------------------------------------------+
|                      PostgreSQL                             |
|   - raw: Ingested source CSV tables                         |
|   - staging: Cleaned, typed, surrogate keys                 |
|   - analytics: Dimensional star schema (facts & dims)       |
+-------------------------------------------------------------+
```

---

## Implementation Roadmap

- [x] **Phase 1: Dataset exploration and data quality assessment** *(Completed)*
- [x] **Phase 2: PostgreSQL setup and data ingestion** *(Completed)*
- [x] **Phase 3: Data modelling and SQL analytics** *(Completed)*
- [x] **Phase 4: Python analytical engine and Streamlit dashboard** *(Completed)*
- [x] **Phase 5: Local LLM integration using Ollama (Qwen 2.5 3B)** *(Completed)*
- [x] **Phase 6: RAG implementation using LangChain and ChromaDB** *(Completed)*
- [x] **Phase 7: SQL agent and tool orchestration** *(Completed)*
- [x] **Phase 8: Business investigation workflow** *(Completed)*
- [ ] **Phase 9: Testing, evaluation, and performance improvements**
- [ ] **Phase 10: Documentation and portfolio release**

---

## Phase 1 Summary: Key Findings & Data Engineering Safeguards

1. **Grain Distinction on Customers:**
   - `customer_id` is a 1:1 order token (99,441 records).
   - `customer_unique_id` represents true unique human individuals (96,096 individuals, 2,997 repeat buyers, 3.12% repeat purchase rate).
   - *Rule:* Customer retention and repeat purchase rate must aggregate by `customer_unique_id`.
2. **Cardinality & Join Fan-Out Prevention:**
   - 9,803 orders have multiple items; 2,961 orders have multiple payment slices.
   - Naively joining order items and payments on `order_id` inflates rows from 112,650 to 117,601 (a 4.4% artificial inflation on revenue).
   - *Rule:* Facts are partitioned into `fact_orders`, `fact_order_items`, and `fact_payments`.
3. **Revenue Baselines (Delivered Orders):**
   - Delivered GMV (Item price only): **R$ 13,221,498.11**
   - Delivered Freight: **R$ 2,202,965.54**
   - Delivered Total Revenue (Items + Freight): **R$ 15,424,463.65**
   - Delivered Total Payments: **R$ 15,422,461.77**
   - Average Order Value (AOV): **R$ 159.88**
4. **Data Cleansing Rules:**
   - Two categories (`pc_gamer`, `portateis_cozinha_e_preparadores_de_alimentos`) and null categories handled via fallback translations in `dim_products`.
   - 547 orders with multiple reviews are deduplicated to the latest answer timestamp for 1:1 order views.

