# InsightIQ End-User Guide & Analytical Playbook

Welcome to **InsightIQ**, an Agentic Business Intelligence Platform designed for business analysts, product managers, data engineers, and corporate executives.

---

## 1. Navigating the Streamlit Studio

InsightIQ is organized into 8 modular analytics and AI investigation workspaces accessible via the sidebar:

```
InsightIQ Studio
├── 📊 1_Executive_Dashboard.py     -> High-level revenue, order volume, AOV, and customer metrics
├── 📈 2_Sales_Analytics.py         -> Monthly revenue growth, product category rankings, state maps
├── 👥 3_Customer_Analytics.py      -> RFM segmentation, repeat buyers, customer lifetime value
├── 🚚 4_Operations_Logistics.py    -> Delivery transit times, delay distribution, seller compliance
├── 🔬 5_Business_Investigation.py   -> Automated root-cause decomposition & delay cliff analysis
├── 💬 6_AI_Analyst.py              -> Natural language multi-tool conversational assistant
├── 📑 7_Reports.py                 -> Downloadable Executive Business Performance briefings
└── 🎯 8_Evaluation_Framework.py    -> Automated 35-question regression benchmark scorecard
```

---

## 2. Using the AI Analyst (`6_AI_Analyst.py`)

The AI Analyst is powered by an autonomous multi-tool orchestrator that understands natural language, classifies intent, generates safe read-only SQL, searches enterprise documentation, executes statistical routines, and presents transparent execution traces.

### Selecting Tool Modes (`Mode Override`)
By default, the agent runs in `Auto-Detect` mode, dynamically selecting the best tool or combining tools. You can explicitly constrain execution using the sidebar dropdown:
- **`Auto-Detect` (Default):** Dispatches SQL, RAG, Python, or Compound tools dynamically.
- **`SQL Only`:** Constrains the agent strictly to relational database queries against the PostgreSQL star schema.
- **`Knowledge Base (RAG) Only`:** Constrains the agent strictly to metric definitions, data dictionary, and business rules.
- **`Python Analytics Only`:** Executes native Python routines for statistical anomalies, correlations, or RFM segments.

### Example Prompts by Business Domain

#### 1. Sales & Revenue Analytics
- *"What is our total delivered revenue and how much was freight?"*
- *"Which product categories generate the highest sales volume?"*
- *"Show sales performance across Brazilian states. Which state is number one?"*
- *"What was the highest revenue month and how much did we make?"*

#### 2. Customer Retention & RFM Segmentation
- *"How many distinct customers made repeat purchases?"*
- *"What is our overall repeat purchase rate?"*
- *"What customer segments generate the most revenue in our RFM model?"*
- *"List our top 10 highest-spending customers."*

#### 3. Operations & Delivery Logistics
- *"What is the average delivery lead time in days?"*
- *"What percentage of orders are delivered on time?"*
- *"Which product categories suffer from the longest delivery delays?"*
- *"Which sellers have the highest cancellation rates?"*

#### 4. Business Knowledge & Metric Definitions
- *"How is average order value calculated?"*
- *"What is the difference between customer_id and customer_unique_id?"*
- *"What criteria qualify an order as delivered revenue?"*
- *"Explain the database star schema relationships."*

#### 5. Complex Compound Queries
- *"What is our delivered revenue and how is it defined in our business rules?"*
- *"Show monthly sales for 2017 and explain why November spiked."*

---

## 3. v1.1 Advanced Agentic Capabilities

### 1. Conversational Multi-Turn Memory & Follow-Up Questions
The AI Analyst retains sliding-window memory across conversation turns within each session. You can ask natural follow-up questions without repeating preceding context:
1. **Turn 1:** *"What was total revenue in 2017?"*
2. **Turn 2:** *"Filter that down to São Paulo customer orders."*
3. **Turn 3:** *"What about health and beauty products?"*

The agent's `ConversationalMemoryManager` and intent classifier automatically detect coreference triggers (`"filter that down"`, `"break that down"`, `"what about"`, `"it"`, `"that"`), inspect preceding turn SQL and entities, and rewrite the follow-up question into an unambiguous query before dispatching.

### 2. Real-Time Token Streaming (Typewriter Effect)
Executive answers stream live into the Streamlit studio using token-level generators with micro-delays (`st.write_stream`). Token streams provide immediate visual feedback, reducing perceived latency while the agent articulates deep analytical insights.

### 3. Voice Query Input (Local Speech-to-Text)
You can speak directly to the AI Analyst:
- Click the **🎙️ Spoken Voice Query** expander.
- Record your question using your workstation microphone via `st.audio_input`.
- The local `SpeechService` inspects the audio stream (WAV, WebM, Ogg, MP3) and transcribes your voice query.
- Alternatively, select from pre-configured enterprise spoken questions to simulate voice interaction with one click.

---

## 4. Business Investigation Studio (`5_Business_Investigation.py`)

The Investigation Studio provides automated analytical workflows that mathematically dissect anomalies rather than relying on superficial summaries:

### 1. Revenue Variance Decomposition
- Mathematical volume-price decomposition:
  $$\Delta \text{Revenue} = (\Delta \text{Orders} \times \text{AOV}_{\text{prior}}) + (\Delta \text{AOV} \times \text{Orders}_{\text{curr}})$$
- Instantly informs executives whether a revenue drop was driven by customer acquisition drops or smaller basket sizes.

### 2. Satisfaction Driver Analysis (The 3-Day Delay Cliff)
- Dissects review score deterioration across granular delay brackets:
  - **On-Time Orders:** 4.29 ★ average rating (only 6.6% 1-star reviews).
  - **1–2 Days Delayed:** 3.73 ★ average rating.
  - **3–5 Days Delayed (The Cliff):** Severe drop to 2.60 ★ (45.1% 1-star reviews).
  - **6–10 Days Delayed:** 1.80 ★ average rating (67.2% 1-star reviews).
- **Executive Rule:** Proactive customer interventions and carrier escalations must trigger prior to day 3 of delay.

### 3. Understanding Causation Guardrails
- In all statistical outputs, InsightIQ includes explicit causal disclaimers. For example:
  > *"Correlation ($r = -0.27$) between delivery delay and low review scores does not establish sole causality. Unobserved factors such as product defect rate, packaging damage, and seller responsiveness also significantly impact review scores."*

---

## 4. Executive Briefings & Reports (`7_Reports.py`)

Stakeholders can compile and export end-to-end business briefings:
1. Navigate to **`7_Reports`**.
2. Select report template (Executive Performance Report, Operational Health, or Seller Audit).
3. Click **"Generate Report"** to run live aggregations across sales, satisfaction, anomalies, and strategic actions.
4. Export as **Markdown (`.md`)** for executive documentation, **PDF Briefing (`.pdf`)** styled with corporate KPI grids and anomaly audits for boardroom presentations, or **JSON (`.json`)** for automated BI ingestion.

---

## 5. Evaluation Framework (`8_Evaluation_Framework.py`)

The evaluation studio gives teams full transparency into agent accuracy and regression resistance:
- Inspect overall pass rate (currently **91.43%**).
- Filter the 35 benchmark test logs by category or pass/fail status.
- Analyze latency scatterplots to identify query bottlenecks.
- Run live evaluation slices on demand with configurable question limits.

