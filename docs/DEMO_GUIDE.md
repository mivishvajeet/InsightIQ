# 🎬 InsightIQ: Platform Walkthrough, Demo Guide & AI Integration

> **A comprehensive visual guide demonstrating how to use InsightIQ, how AI is deeply integrated into every analytical layer, and how it solves real-world e-commerce business problems.**

---

## 📽️ 1. Interactive Walkthrough & Video Demonstration

An automated, high-definition screen recording of the entire application walkthrough is available:

- **Full HD Session Video:** [insightiq_walkthrough.webm](file:///Users/mivishvajeet/InsightHQ/docs/assets/videos/insightiq_walkthrough.webm) *(9.9 MB WebM recording)*
- **Live Script to Re-Record:** Run `python scripts/capture_demo_assets.py` anytime to re-capture all screens and re-record the walkthrough video.

### Animated Walkthrough Overview
Below is the continuous animated walkthrough touring all 8 workspaces:

![InsightIQ Animated Walkthrough](file:///Users/mivishvajeet/InsightHQ/docs/assets/screenshots/insightiq_walkthrough.gif)

---

## 🧠 2. How AI is Integrated Into InsightIQ

InsightIQ avoids the pitfalls of generic LLM wrappers by implementing a **modular, multi-tool agentic architecture** that enforces strict deterministic boundaries between natural language understanding, database access, statistical computation, and generative synthesis.

```
                      +------------------------------------------+
                      |         User Business Question           |
                      | "Why did revenue drop between Jan & Feb?" |
                      +--------------------+---------------------+
                                           |
                                           v
                             +---------------------------+
                             |   AgentIntentClassifier   |
                             | (Heuristics + Routing LLM)|
                             +-------------+-------------+
                                           |
                                           v
                      +------------------------------------------+
                      |            OrchestratorAgent             |
                      |  (Single Coordinator / Step Trace Engine)|
                      +--------------------+---------------------+
                                           |
          +-------------------+------------+------------+--------------------+
          |                   |                         |                    |
          v                   v                         v                    v
+-------------------+ +-------------------+   +--------------------+ +--------------------+
| SQLAnalyticsTool  | | RAGRetrievalTool  |   |PythonAnalyticsTool | |BusinessInvestigator|
| - Qwen 2.5 3B     | | - ChromaDB Vector |   | - KPI Engine       | | - Variance Decomp|
| - AST Validator   | | - Nomic Embeddings|   | - RFM Segmentation | | - Delay Cliff (3d)|
| - Self-Healing    | | - Chunk Citations |   | - Z-Score / IQR    | | - Causal Guardrails|
+---------+---------+ +---------+---------+   +----------+---------+ +----------+---------+
          |                     |                        |                      |
          +---------------------+------------+-----------+----------------------+
                                             |
                                             v
                             +-------------------------------+
                             |    AgentResponseSynthesizer   |
                             | - Anti-Hallucination Grounding|
                             | - Step-by-Step Transparency   |
                             +---------------+---------------+
                                             |
                                             v
                      +------------------------------------------+
                      |     Verified Answer + Execution Trace    |
                      +------------------------------------------+
```

### Key AI Subsystems & Innovations:

### 1. Autonomous Multi-Tool Orchestrator (`OrchestratorAgent`)
- Instead of relying on brittle prompt-chaining, a single coordinator agent dispatches specialized tools (`sql_analytics_tool`, `rag_retrieval_tool`, `python_analytics_tool`, `business_investigation_tool`, `report_generation_tool`).
- Generates a transparent, auditable **Execution Step Trace** recording every step name, tool dispatched, duration in seconds, and status.

### 2. Intelligent Intent Classification (`AgentIntentClassifier`)
- Classifies user intent into distinct modes: `sql`, `rag`, `python`, `investigation`, `report`, or `hybrid`.
- Employs domain-specific regex heuristics and exemplar matching.
- **Safety Routing:** Detects out-of-scope non-ecommerce queries (e.g. stock tickers, weather) and routes them to RAG with strict limitation disclosure rules, preventing hallucinations.

### 3. Natural Language to SQL Generation with Self-Healing (`SQLGenerator`)
- Translates conversational business inquiries into PostgreSQL queries.
- Conditioned on star schema DDL prompts, business metric definitions, and few-shot exemplars.
- **Automated Self-Healing Loop:** If PostgreSQL throws a syntax or column error, the exception is caught, packaged with the failed query into a reflection prompt, and re-executed with automatic correction.

### 4. SQL AST Security Validator (`SQLValidator`)
- Every generated SQL string is parsed into an Abstract Syntax Tree (AST) before touching the database:
  - **Statement Whitelist:** Strictly permits `SELECT` and `WITH` (CTE) statements.
  - **Mutation Blacklist:** Blocks `DROP`, `ALTER`, `TRUNCATE`, `INSERT`, `UPDATE`, `DELETE`, and `GRANT`.
  - **Schema Isolation:** Blocks access to `raw.*` and `staging.*` tables, enforcing access only to `analytics.*`.
  - **Denial-of-Service Defense:** Injects `LIMIT 500` if absent and enforces a hard 10-second query timeout.
  - **Least Privilege:** Connects via the `insightiq_readonly` database role.

### 5. Semantic Knowledge Retrieval (RAG) (`RAGPipeline`)
- Resolves organizational questions ("How is AOV calculated?", "Difference between customer_id and customer_unique_id?").
- Uses **ChromaDB** with **Nomic Embed Text** (768-dimensional local embeddings).
- Knowledge base markdown documents are section-aware chunked into 27 dense semantic vectors.
- Returns precise citations (file source, section heading, chunk ID, relevance score).

### 6. Mathematical Business Investigation Engines
- **Revenue Variance Decomposition:** Dissects month-over-month revenue changes mathematically into volume vs price effects:
  $$\Delta \text{Revenue} = (\Delta \text{Orders} \times \text{AOV}_{\text{prior}}) + (\Delta \text{AOV} \times \text{Orders}_{\text{curr}})$$
- **Satisfaction Delay Cliff:** Quantifies non-linear review score collapse: on-time orders average **4.29 ★**, while orders delayed 3–5 days plunge to **2.60 ★** (45.1% 1-star reviews).
- **Mandatory Causal Guardrails:** Enforces explicit disclaimers ($r = -0.27$ correlation does not prove sole causation), preventing agents from making false attribution claims.

### 7. Lexical Grounding & Anti-Hallucination (`AgentResponseSynthesizer`)
- Synthesized natural language answers are cross-checked against returned data rows and markdown citations.
- Tested and achieved a **97.14% answer grounding accuracy** across the benchmark suite.

### 8. Regression Benchmark & Telemetry Engine (`BenchmarkEvaluator`)
- Automated evaluation testing **35 standardized business questions** across 8 analytical categories.
- Evaluates 5 orthogonal dimensions: Tool-Selection Accuracy (**100%**), Execution Success (**100%**), SQL Correctness (**91.43%**), Answer Grounding (**97.14%**), and Security Handling (**100%**).
- **Overall Benchmark Pass Rate: 91.43%** (exceeding the 90% production target).

---

## 🖥️ 3. Step-by-Step Module Walkthrough

Here is how each workspace functions, accompanied by live full-rendered screenshots:

---

### Workspace 1: Welcome & System Architecture
* **Purpose:** Introduces the platform architecture, data warehouse star schema, local AI stack, and provides navigation across all modules.

![Landing Page](file:///Users/mivishvajeet/InsightHQ/docs/assets/screenshots/01_landing_page.png)

---

### Workspace 2: Executive Performance Dashboard (`1_Executive_Dashboard.py`)
* **Purpose:** Real-time visibility into executive financial metrics, sales trajectories, and fulfillment baselines.
* **Key Metrics Grounded on Data:**
  * **Total Delivered Revenue:** R$ 15,424,463.65 across 96,478 delivered orders.
  * **Delivered GMV:** R$ 13,221,498.11 (Item price) + R$ 2,202,965.54 (Freight revenue).
  * **Average Order Value (AOV):** R$ 159.88.
  * **On-Time Delivery Rate:** 91.89%.

![Executive Dashboard](file:///Users/mivishvajeet/InsightHQ/docs/assets/screenshots/02_executive_dashboard.png)

---

### Workspace 3: Sales Analytics & Category Performance (`2_Sales_Analytics.py`)
* **Purpose:** Multi-dimensional breakdown of sales volume, month-over-month growth rates, product category rankings, and geographic state heatmaps.
* **Insights:**
  * Top Category by Sales: `bed_bath_table` (R$ 1.71M), followed by `health_beauty` (R$ 1.44M).
  * Geographic Concentration: São Paulo (`SP`) represents over 37% of total revenue.

![Sales Analytics](file:///Users/mivishvajeet/InsightHQ/docs/assets/screenshots/03_sales_analytics.png)

---

### Workspace 4: Customer Analytics & RFM Segmentation (`3_Customer_Analytics.py`)
* **Purpose:** Unveils the true customer grain and clusters customers using Recency, Frequency, and Monetary (RFM) modeling.
* **Insights:**
  * **Customer Grain Distinction:** While `customer_id` is an order token (99,441 records), there are **96,096 unique human buyers** (`customer_unique_id`).
  * **Repeat Purchase Rate:** 3.12% (2,997 repeat buyers), showing high customer acquisition reliance and large opportunities for retention loyalty programs.

![Customer Analytics](file:///Users/mivishvajeet/InsightHQ/docs/assets/screenshots/04_customer_analytics.png)

---

### Workspace 5: Operations & Delivery Logistics (`4_Operations_Logistics.py`)
* **Purpose:** Diagnoses the fulfillment supply chain, delivery lead time distributions, and shipping carrier performance across Brazilian states.
* **Insights:**
  * Mean delivery lead time is **12.5 days**.
  * Remote northern states (RR, AP, AM) experience average transit times exceeding 25 days.

![Operations and Logistics](file:///Users/mivishvajeet/InsightHQ/docs/assets/screenshots/05_operations_logistics.png)

---

### Workspace 6: Business Investigation Studio (`5_Business_Investigation.py`)
* **Purpose:** Automated root-cause investigation algorithms that mathematically dissect anomalies.
* **Capabilities:**
  * **Variance Decomposition:** Dissects revenue drops into volume vs basket-size effects.
  * **The 3-Day Delay Cliff:** Pinpoints that at $\ge 3$ days of transit delay, customer 1-star ratings jump from 6.6% to 45.1%.

![Business Investigation](file:///Users/mivishvajeet/InsightHQ/docs/assets/screenshots/06_business_investigation.png)

---

### Workspace 7: Autonomous AI Analyst Studio (`6_AI_Analyst.py`)
* **Purpose:** Multi-tool conversational interface with complete execution transparency.
* **Capabilities:**
  * Shows step-by-step tool traces (Intent -> Retrieval -> SQL -> Synthesis).
  * Displays generated SQL syntax with direct copy/inspect controls.
  * Provides sortable data tables with CSV export and markdown source citations.

![AI Analyst Studio](file:///Users/mivishvajeet/InsightHQ/docs/assets/screenshots/07_ai_analyst.png)

---

### Workspace 8: Executive Reports & Intelligence Briefings (`7_Reports.py`)
* **Purpose:** Generates comprehensive, boardroom-ready business briefings combining financial health, operational bottlenecks, historical anomalies, and strategic actions.
* **Export Options:** One-click download as **Markdown (`.md`)** or **JSON (`.json`)**.

![Executive Reports](file:///Users/mivishvajeet/InsightHQ/docs/assets/screenshots/08_reports.png)

---

### Workspace 9: Evaluation Framework & Benchmark Scorecard (`8_Evaluation_Framework.py`)
* **Purpose:** Real-time observability into model accuracy, regression benchmarks, latency scatterplots, and live test slice execution.
* **Current Score:** **91.43% Overall Pass Rate** across 35 business questions.

![Evaluation Framework](file:///Users/mivishvajeet/InsightHQ/docs/assets/screenshots/09_evaluation_framework.png)

---

## 🚀 4. How to Run Everything Locally

### 1. Verify Complete System Health (1-Click CLI)
```bash
python scripts/verify_system.py
```
*Tests all 6 layers: Database, Ollama, ChromaDB, SQL Security, Multi-Tool Agent, and Benchmark Telemetry.*

### 2. Start the Interactive Streamlit Dashboard
```bash
streamlit run frontend/app.py
```
Open **[http://localhost:8501](http://localhost:8501)** in your browser.

### 3. Start the FastAPI REST API
```bash
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```
Open interactive Swagger documentation at **[http://localhost:8000/docs](http://localhost:8000/docs)**.

### 4. Run the Full Test Suite
```bash
pytest backend/tests/ -v
```

### 5. Re-Run the Automated Screen Capture & Walkthrough Video Recorder
```bash
python scripts/capture_demo_assets.py
```
*Automatically navigates all pages, captures screenshots, renders the animated GIF, and records the session video.*
