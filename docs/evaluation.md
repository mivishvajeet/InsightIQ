# InsightIQ Evaluation Framework & Benchmark Methodology

This document outlines the evaluation architecture, benchmark methodology, scoring algorithms, and empirical test results for **InsightIQ** (an Agentic Business Intelligence Platform running on the Olist Brazilian E-Commerce dataset).

---

## 1. Executive Summary

The InsightIQ evaluation framework implements rigorous, objective regression testing across **35 diverse business questions** spanning 8 core analytical domains. Tests evaluate the complete end-to-end multi-agent orchestration lifecycle—from natural language parsing and intent routing to SQL generation, schema isolation, vector knowledge retrieval, statistical computation, answer grounding, and safety guardrails.

### Benchmark Telemetry Summary (Latest Run)
- **Total Questions Evaluated:** 35
- **Passed Questions:** 32
- **Overall Pass Rate:** **91.43%** *(Target: >90%)*
- **Tool-Selection Accuracy:** **100.00%**
- **Execution Success Rate:** **100.00%**
- **SQL Result Correctness:** **91.43%**
- **Answer Grounding (Anti-Hallucination):** **97.14%**
- **Security & Error Handling:** **100.00%**
- **Average Latency:** **10.62 seconds**
- **Total Benchmark Duration:** **371.65 seconds**

---

## 2. Category Performance Breakdown

| Analytical Domain | Questions | Passed | Pass Rate (%) | Primary Engine Tested |
| :--- | :---: | :---: | :---: | :--- |
| **Sales Analytics** | 7 | 5 | 71.4% | `sql_analytics_tool` (PostgreSQL star schema views) |
| **Customer Analytics** | 6 | 5 | 83.3% | `sql_analytics_tool` / `python_analytics_tool` (RFM segments) |
| **Operational Analytics** | 5 | 5 | 100.0% | `sql_analytics_tool` (Delivery lead times, transit rates) |
| **Knowledge Retrieval** | 6 | 6 | 100.0% | `rag_retrieval_tool` (ChromaDB + nomic-embed-text) |
| **Business Investigation** | 6 | 6 | 100.0% | `business_investigation_tool` (Decomposition & cliff analysis) |
| **Compound / Hybrid** | 1 | 1 | 100.0% | RAG + SQL multi-step synthesis |
| **Executive Reports** | 1 | 1 | 100.0% | `report_generation_tool` (Executive summary compilation) |
| **Edge Cases & Unsupported** | 3 | 3 | 100.0% | AST SQL Validator & RAG Limitation Disclosures |
| **Total / Overall** | **35** | **32** | **91.43%** | **Full Multi-Tool Orchestrator** |

---

## 3. Multi-Dimensional Scoring Engine

Each benchmark question is scored across five orthogonal dimensions:

```
                  ┌───────────────────────────────────────────────┐
                  │              Question Evaluation              │
                  └───────────────────────┬───────────────────────┘
                                          │
       ┌──────────────────┬───────────────┼───────────────┬──────────────────┐
       ▼                  ▼               ▼               ▼                  ▼
┌──────────────┐   ┌──────────────┐┌──────────────┐┌──────────────┐   ┌──────────────┐
│Tool Selection│   │  Execution   ││ Correctness  ││   Answer     │   │   Security   │
│  Accuracy    │   │   Success    ││    Score     ││  Grounding   │   │ & Guardrails │
│  (0.0 / 1.0) │   │ (True/False) ││ (0.0 - 1.0)  ││ (0.0 - 1.0)  │   │ (0.0 - 1.0)  │
└──────────────┘   └──────────────┘└──────────────┘└──────────────┘   └──────────────┘
```

### 1. Tool-Selection Accuracy (`tool_selection_score`)
- Verifies that the agent correctly routes user intent to the required tool:
  - Exact intent and tool match = `1.0`
  - Valid tool dispatched despite ambiguous phrasing = `1.0`
  - Tool dispatch failure / misrouting = `0.0`

### 2. Execution Success (`execution_success`)
- Verifies that the tool executed without unhandled runtime exceptions or crashes.

### 3. Correctness Score (`correctness_score`)
- **Scalar Metric:** Compares numerical result with ground truth within allowed tolerance (`abs(actual - expected) <= tolerance`).
- **Ranking Metric:** Verifies that returned top entities match ground truth ordering (e.g., SP as top state; bed_bath_table as top category).
- **Time-Series Metric:** Checks minimum returned row counts and date granularity.
- **RAG Relevance:** Verifies that context citations match expected source documents.
- **Investigation / Report Success:** Verifies structured evidence compilation and causal guardrail inclusion.

### 4. Answer Grounding Score (`grounding_score`)
- Lexical anti-hallucination verification. Checks that the synthesized natural language response explicitly mentions the key quantitative facts, figures, and domain entities from ground truth:
  $$\text{Grounding Score} = \frac{\sum_{i=1}^{N} \mathbb{I}(\text{phrase}_i \in \text{Answer})}{N}$$

### 5. Security & Limitation Handling (`error_handling_score`)
- **SQL Injection Defense:** Verifies that destructive queries (`DROP TABLE`, `UPDATE`, `DELETE`) are trapped and blocked by `SQLValidator` AST inspection with `1.0` score.
- **Out-of-Bounds Queries:** Verifies that queries for non-existent years (e.g., 2035) return 0 rows cleanly without crashing or inventing synthetic data.
- **Out-of-Scope Topics:** Verifies that queries on external domains (e.g., Apple NASDAQ stock, weather) explicitly disclose database limitations and refuse to hallucinate.

---

## 4. Benchmark Dataset Composition

The 35 questions defined in `evaluation/benchmark_questions.json` encompass:
1. **Q01–Q07 (Sales Analytics):** Revenue trends, top categories, state sales distribution, AOV (R$ 159.88), peak revenue month (Nov 2017), total delivered revenue (R$ 15,424,463.65), and GMV excluding freight (R$ 13,221,498.11).
2. **Q08–Q13 (Customer Analytics):** Repeat customer count (2,997), repeat purchase rate (3.12%), customer distribution across 27 states, RFM customer segment revenue contributions, and high-value customer identification.
3. **Q14–Q18 (Operational Analytics):** Average delivery lead time (12.5 days), delivery delay impact on review scores, problematic seller cancellation rates, categories with longest delivery lead times, and platform on-time delivery rate (91.89%).
4. **Q19–Q24 (Knowledge Retrieval):** Business definitions (customer retention, AOV, delivered order criteria), database star schema relationships, freight subsidy policies, and difference between `customer_id` (transaction-scoped) and `customer_unique_id` (person-scoped).
5. **Q25–Q30 (Business Investigation):** MoM revenue decline decomposition (Jan–Feb 2018), satisfaction decline root cause (3-day delay cliff), underperforming categories, and statistical revenue anomaly detection (Black Friday 2017).
6. **Q31 (Compound Query):** Delivers revenue calculation paired with business definition in a single multi-step response.
7. **Q32 (Executive Reports):** Formal executive business report compilation.
8. **Q33–Q35 (Edge Cases & Security):** NASDAQ stock inquiry (out-of-scope disclosure), Year 2035 inquiry (out-of-bounds 0-row handling), and `DROP TABLE` SQL injection injection attempt (AST security blocking).

---

## 5. Execution & Verification

### Running Evaluation via CLI
```bash
# Run full 35-question suite
python -m evaluation.run_evaluation

# Run specific category slice
python -m evaluation.run_evaluation --category "Sales Analytics"

# Run quick sample with limit
python -m evaluation.run_evaluation --limit 5
```

### Running Failure Diagnostics
```bash
python -m evaluation.failure_analysis
```

### Running Automated Pytest Suite
```bash
pytest backend/tests/test_evaluation_benchmark.py -v
```

### Web UI Benchmark Studio
Navigate to `Streamlit > 🎯 8_Evaluation_Framework` to inspect interactive scorecards, filterable log tables, category pass rates, latency scatterplots, and trigger live slice evaluations.
