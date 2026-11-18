# InsightIQ System Architecture & Security Specification

InsightIQ is an enterprise-grade Agentic Business Intelligence Platform running locally on PostgreSQL 16, ChromaDB, and local Ollama LLMs (`qwen2.5:3b` + `nomic-embed-text`).

---

## 1. High-Level Architecture

The platform follows a layered, decoupled service architecture:

```mermaid
flowchart TD
    subgraph UI["Presentation Layer (Streamlit)"]
        DASH["1_Executive_Dashboard.py"]
        SALES["2_Sales_Analytics.py"]
        CUST["3_Customer_Analytics.py"]
        OPS["4_Operations_Logistics.py"]
        INV["5_Business_Investigation.py"]
        AGENT_UI["6_AI_Analyst.py"]
        REP["7_Reports.py"]
        EVAL_UI["8_Evaluation_Framework.py"]
    end

    subgraph API["API Gateway Layer (FastAPI)"]
        ROUTER["FastAPI Router (/api)"]
        PYDANTIC["Pydantic v2 Request/Response Schemas"]
    end

    subgraph ORCH["Orchestration & Reasoning Layer"]
        AGENT["OrchestratorAgent"]
        INTENT["AgentIntentClassifier"]
        REGISTRY["ToolRegistry"]
        SYNTH["AgentResponseSynthesizer"]
    end

    subgraph TOOLS["Tool Execution Subsystems"]
        SQL_TOOL["SQLAnalyticsTool"]
        RAG_TOOL["RAGRetrievalTool"]
        PY_TOOL["PythonAnalyticsTool"]
        INV_TOOL["BusinessInvestigationTool"]
        REP_TOOL["ReportGenerationTool"]
    end

    subgraph STORAGE["Data & AI Infrastructure"]
        PG[("PostgreSQL 16 (Star Schema)\nanalytics.fact_orders\nanalytics.v_monthly_sales")]
        CHROMA[("ChromaDB Vector Store\n(insightiq_knowledge_base)")]
        OLLAMA["Local Ollama Daemon\n(qwen2.5:3b + nomic-embed-text)"]
    end

    UI -->|HTTP / REST| API
    API --> ORCH
    AGENT --> INTENT
    AGENT --> REGISTRY
    REGISTRY --> SQL_TOOL
    REGISTRY --> RAG_TOOL
    REGISTRY --> PY_TOOL
    REGISTRY --> INV_TOOL
    REGISTRY --> REP_TOOL

    SQL_TOOL -->|Read-Only Connection| PG
    SQL_TOOL -->|SQL Prompt & Reflection| OLLAMA
    RAG_TOOL -->|Semantic Vector Search| CHROMA
    RAG_TOOL -->|Text Embeddings| OLLAMA
    PY_TOOL -->|Analytics Queries| PG
    INV_TOOL -->|Variance Decomposition| PG
    REP_TOOL -->|KPI & Metric Synthesis| PG
    AGENT --> SYNTH
    SYNTH -->|Context Synthesis| OLLAMA
```

---

## 2. Multi-Agent Orchestrator Execution Flow

When a user submits a question, the single orchestrator agent executes a deterministic step trace:

```mermaid
sequenceDiagram
    autonumber
    actor User as Business Stakeholder
    participant Orchestrator as OrchestratorAgent
    participant Classifier as AgentIntentClassifier
    participant Registry as ToolRegistry
    participant Tool as Specialized Tool (SQL/RAG/Python)
    participant Validator as SQL AST Validator
    participant DB as PostgreSQL (Read-Only)
    participant Synthesizer as AgentResponseSynthesizer

    User->>Orchestrator: "Why did revenue decline in Feb 2018 and how is GMV defined?"
    Orchestrator->>Classifier: Classify Intent(question)
    Classifier-->>Orchestrator: Intent=Hybrid, Tools=[rag_retrieval_tool, sql_analytics_tool]
    
    rect rgb(240, 248, 255)
        Note over Orchestrator,Tool: Tool Execution Step 1: Knowledge Retrieval
        Orchestrator->>Registry: Dispatch(rag_retrieval_tool, query="how is GMV defined")
        Registry->>Tool: Execute RAG search
        Tool-->>Registry: Citations [metric_definitions.md, sales_business_rules.md]
        Registry-->>Orchestrator: RAG Results & Documentation
    end

    rect rgb(245, 255, 245)
        Note over Orchestrator,DB: Tool Execution Step 2: Relational SQL Analytics
        Orchestrator->>Registry: Dispatch(sql_analytics_tool, question="Feb 2018 revenue")
        Registry->>Tool: Generate SQL
        Tool->>Validator: Validate AST(sql)
        Validator-->>Tool: Valid (SELECT only, analytics schema, limit enforced)
        Tool->>DB: Execute Query (10s timeout, read-only transaction)
        DB-->>Tool: Structured Record Set
        Tool-->>Registry: SQL Results + Data Table
        Registry-->>Orchestrator: SQL Execution Artifact
    end

    Orchestrator->>Synthesizer: Synthesize(question, tool_outputs)
    Synthesizer-->>Orchestrator: Grounded Natural Language Answer + Citations
    Orchestrator-->>User: Final Response with Step-by-Step Execution Trace
```

---

## 3. Database Schema Architecture

PostgreSQL is partitioned into three strictly isolated schemas:

1. **`raw` (Source Ground Truth):**
   - Direct ingestion of 9 Olist CSV files (1,550,922 total records).
   - Ingested with verbatim fidelity without destructive mutations.
2. **`staging` (Cleaning & Surrogate Keys):**
   - Cleaned timestamps, standardized ISO currency columns, and English category translations.
   - Surrogate integer keys for performant join indexing.
3. **`analytics` (Star Schema Marts & Views):**
   - **Dimension Tables:** `dim_date`, `dim_customers`, `dim_products`, `dim_sellers`.
   - **Fact Tables:** `fact_orders` (99,441 rows), `fact_order_items` (112,650 rows), `fact_payments` (103,886 rows), `fact_reviews` (99,224 rows).
   - **Analytical Views:**
     - `v_monthly_sales`: Monthly GMV, freight, revenue, and order counts.
     - `v_category_performance`: Category rankings, item counts, delivered revenue.
     - `v_state_sales_distribution`: Geographic concentration across all 27 Brazilian states.
     - `v_customer_rfm_segments`: Recency, frequency, and monetary customer clustering.
     - `v_seller_performance`: Fulfillment reliability and on-time shipping rates.

---

## 4. Security & Safety Architecture

InsightIQ enforces enterprise-grade security controls preventing data exfiltration, accidental mutations, SQL injections, and generative hallucinations:

### 1. Database Privilege Isolation
- AI Agent operations connect exclusively via the `insightiq_readonly` user:
  ```sql
  GRANT SELECT ON ALL TABLES IN SCHEMA analytics TO insightiq_readonly;
  REVOKE ALL ON SCHEMA raw, staging FROM insightiq_readonly;
  ```
- Any attempt to execute `INSERT`, `UPDATE`, `DELETE`, or `DROP` triggers an immediate PostgreSQL engine permission denial.

### 2. SQL AST Inspection & Security Validator
Before query execution, `SQLValidator` parses the SQL AST:
- **Statement Whitelist:** Strictly permits `SELECT` and `WITH` (CTE) statements.
- **Destructive Operation Blacklist:** Traps and rejects `DROP`, `ALTER`, `TRUNCATE`, `INSERT`, `UPDATE`, `DELETE`, `GRANT`, `REVOKE`, `COPY`, and `EXECUTE`.
- **Schema Boundary Enforcement:** Prohibits direct access to `raw.*` and `staging.*` tables.
- **Automatic Limit Injection:** Automatically appends `LIMIT 500` if absent to prevent runaway memory usage.
- **Statement Timeout:** Every query is executed with `statement_timeout = 10000` (10 seconds max).

### 3. Causal Guardrails in Statistical Inference
- When analyzing correlations (e.g. delivery delay vs customer review scores, $r = -0.27$), the analytical tools enforce strict disclaimers stating that correlation does not establish sole causality.
- Prevents the agent from falsely asserting that operational delays are the exclusive cause of negative customer feedback.

### 4. Lexical Grounding & Anti-Hallucination
- Generated answers are scored against required ground truth facts and numbers.
- If data is absent, the agent is constrained by prompt rules to disclose the limitation rather than invent plausible approximations.
