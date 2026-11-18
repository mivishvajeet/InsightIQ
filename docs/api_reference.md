# InsightIQ REST API Reference

The InsightIQ FastAPI backend exposes RESTful endpoints for natural language SQL analytics, RAG knowledge retrieval, Python statistical computation, multi-agent orchestration, business investigations, and automated evaluation.

- **Base URL:** `http://localhost:8000/api`
- **Interactive OpenAPI Documentation:** `http://localhost:8000/docs`
- **Alternative ReDoc UI:** `http://localhost:8000/redoc`

---

## 1. System Health & Infrastructure

### `GET /api/health`
Checks PostgreSQL database connectivity and local Ollama daemon status.

**Example Request:**
```bash
curl -X GET http://localhost:8000/api/health
```

**Example Response:**
```json
{
  "status": "ok",
  "database_connected": true,
  "ollama_connected": true
}
```

---

## 2. Multi-Tool Agent Orchestration

### `POST /api/agent/query`
The primary conversational intelligence endpoint. Dispatches business queries through the single orchestrator agent, executing tools (SQL, RAG, Python, Investigation, Reporting) and returning step-by-step traces with anti-hallucination grounded responses.

**Request Body:**
- `question` (string, required): The natural language business inquiry.
- `mode_override` (string, optional): Forced tool mode (`auto`, `sql`, `rag`, `python`, `hybrid`). Default is `auto`.
- `top_k` (integer, optional): Number of context chunks for RAG operations (default: 4).

**Example Request:**
```bash
curl -X POST http://localhost:8000/api/agent/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is the monthly revenue trend and how is delivered revenue defined?",
    "mode_override": "auto",
    "top_k": 4
  }'
```

**Example Response:**
```json
{
  "question": "What is the monthly revenue trend and how is delivered revenue defined?",
  "final_answer": "Delivered revenue is defined as the net monetary value of customer orders that completed delivery, comprising product price plus freight charges. Across the platform history, total delivered revenue reached R$ 15,424,463.65 across 96,478 delivered orders. Monthly sales grew steadily from 2016 through mid-2018, peaking in November 2017 during Black Friday at R$ 1,194,882.80.",
  "intent": "rag",
  "tools_used": ["rag_retrieval_tool", "sql_analytics_tool"],
  "execution_steps": [
    {
      "step_number": 1,
      "step_name": "Intent Classification",
      "tool_name": null,
      "description": "Classified intent as compound RAG & SQL inquiry",
      "status": "success",
      "duration_seconds": 0.05
    },
    {
      "step_number": 2,
      "step_name": "Knowledge Retrieval",
      "tool_name": "rag_retrieval_tool",
      "description": "Retrieved 4 chunks from metric_definitions.md and sales_business_rules.md",
      "status": "success",
      "duration_seconds": 0.22
    },
    {
      "step_number": 3,
      "step_name": "SQL Analytics Query",
      "tool_name": "sql_analytics_tool",
      "description": "Executed validated read-only SQL on analytics.v_monthly_sales",
      "status": "success",
      "duration_seconds": 0.48
    }
  ],
  "sql_query": "SELECT order_month, gmv, freight_revenue, total_delivered_revenue FROM analytics.v_monthly_sales ORDER BY order_month ASC LIMIT 25;",
  "data_table": [
    {"order_month": "2017-11", "gmv": 1010271.37, "freight_revenue": 184611.43, "total_delivered_revenue": 1194882.80}
  ],
  "citations": [
    {
      "source": "metric_definitions.md",
      "title": "Delivered Revenue Definition",
      "section": "Financial Metrics",
      "chunk_id": "chunk_014",
      "relevance_score": 0.88,
      "snippet": "Delivered Revenue is calculated strictly on orders where order_status = 'delivered'..."
    }
  ],
  "total_execution_time_seconds": 4.12,
  "error": null
}
```

---

## 3. Natural Language SQL Engine

### `POST /api/query`
Translates user questions into validated SQL, executes read-only against the analytics dimensional warehouse, and returns structured rows with natural language explanations.

**Request Body:**
- `question` (string, required): Natural language query.
- `execute` (boolean, optional): Whether to execute against database (default: `true`).

**Example Request:**
```bash
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"question": "Which product category generates the highest sales?", "execute": true}'
```

**Example Response:**
```json
{
  "question": "Which product category generates the highest sales?",
  "sql": "SELECT category_name_english, total_revenue FROM analytics.v_category_performance ORDER BY total_revenue DESC LIMIT 5;",
  "explanation": "Queries top categories from v_category_performance sorted by total delivered revenue.",
  "execution_time_seconds": 0.21,
  "row_count": 5,
  "columns": ["category_name_english", "total_revenue"],
  "data": [
    {"category_name_english": "bed_bath_table", "total_revenue": 1712553.67},
    {"category_name_english": "health_beauty", "total_revenue": 1441248.07},
    {"category_name_english": "computers_accessories", "total_revenue": 1059272.40}
  ],
  "error": null
}
```

---

## 4. Analytical KPIs & Statistics

### `GET /api/kpi/summary`
Returns top-level executive business performance KPIs.

**Example Request:**
```bash
curl -X GET http://localhost:8000/api/kpi/summary
```

**Example Response:**
```json
{
  "total_revenue": 15424463.65,
  "total_gmv": 13221498.11,
  "total_freight": 2202965.54,
  "total_orders": 99441,
  "delivered_orders": 96478,
  "aov": 159.88,
  "unique_customers": 96096,
  "repeat_customers": 2997,
  "repeat_purchase_rate_pct": 3.12,
  "avg_review_score": 4.13,
  "avg_delivery_days": 12.5,
  "on_time_rate_pct": 91.89
}
```

### `GET /api/anomalies/revenue`
Performs parametric Z-score and non-parametric IQR outlier detection on daily sales.

**Example Response:**
```json
{
  "metric_analyzed": "daily_revenue",
  "total_days_evaluated": 616,
  "anomalies_detected": 14,
  "top_spike_date": "2017-11-24",
  "top_spike_revenue": 175320.05,
  "top_spike_z_score": 10.44,
  "event_context": "Black Friday 2017"
}
```

### `GET /api/correlations/delivery`
Computes statistical correlation between delivery delays and customer review scores, accompanied by mandatory causal guardrails.

**Example Response:**
```json
{
  "pearson_r": -0.27,
  "spearman_rho": -0.29,
  "sample_size": 96478,
  "p_value": 0.0,
  "delay_cliff_day": 3,
  "on_time_avg_score": 4.29,
  "delayed_avg_score": 2.26,
  "causation_guardrail": "Correlation does not imply sole causation. While delivery delay shows a strong negative association with review score (r = -0.27), unobserved factors such as product defect rate and seller communication also influence ratings."
}
```

---

## 5. RAG Semantic Knowledge Retrieval

### `POST /api/rag/retrieve`
Queries the ChromaDB vector database for semantically similar knowledge chunks.

**Request Body:**
- `query` (string, required): Natural language search phrase.
- `top_k` (integer, optional): Number of chunks to return (default: 4).
- `category` (string, optional): Metadata category filter (`metrics`, `schema`, `business_rules`).

**Example Request:**
```bash
curl -X POST http://localhost:8000/api/rag/retrieve \
  -H "Content-Type: application/json" \
  -d '{"query": "How is customer retention calculated?", "top_k": 2}'
```

---

## 6. Business Investigations & Executive Reports

### `POST /api/investigation/run`
Executes structured root-cause investigations.

**Supported `investigation_type` values:**
- `revenue_anomaly`: Volume vs Price variance decomposition.
- `satisfaction_drivers`: Quantification of the 3-day delay cliff.
- `seller_performance`: Identification of high-cancellation sellers.
- `transit_bottlenecks`: Identification of high-delay transit routes.
- `underperforming_categories`: Identification of high-return / low-margin categories.

**Example Request:**
```bash
curl -X POST http://localhost:8000/api/investigation/run \
  -H "Content-Type: application/json" \
  -d '{
    "investigation_type": "satisfaction_drivers",
    "params": {"delay_cliff_days": 3}
  }'
```

### `GET /api/reports/executive`
Compiles and returns the formal Executive Business Performance Report in Markdown and JSON formats.

---

## 7. Evaluation Framework & Benchmarks

### `GET /api/evaluation/summary`
Retrieves the latest benchmark scorecard across all 35 test questions.

**Example Request:**
```bash
curl -X GET http://localhost:8000/api/evaluation/summary
```

**Example Response:**
```json
{
  "timestamp": "2026-11-18 01:44:27",
  "total_questions": 35,
  "passed_questions": 32,
  "overall_pass_rate_pct": 91.43,
  "metrics": {
    "tool_selection_accuracy_pct": 100.0,
    "execution_success_rate_pct": 100.0,
    "sql_result_correctness_pct": 91.43,
    "answer_grounding_pct": 97.14,
    "error_handling_accuracy_pct": 100.0,
    "average_latency_seconds": 10.62,
    "total_duration_seconds": 371.65
  },
  "category_breakdown": {
    "Sales Analytics": {"total": 7, "passed": 5, "pass_rate_pct": 71.43},
    "Operational Analytics": {"total": 5, "passed": 5, "pass_rate_pct": 100.0},
    "Knowledge Retrieval": {"total": 6, "passed": 6, "pass_rate_pct": 100.0},
    "Business Investigation": {"total": 6, "passed": 6, "pass_rate_pct": 100.0},
    "Edge Cases & Unsupported": {"total": 3, "passed": 3, "pass_rate_pct": 100.0}
  },
  "question_scores": []
}
```

### `POST /api/evaluation/run`
Triggers an automated benchmark evaluation run on demand.

**Request Body:**
- `category` (string, optional): Test specific category slice (e.g., `Sales Analytics`).
- `limit` (integer, optional): Maximum questions to evaluate (default: all).
