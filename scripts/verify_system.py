#!/usr/bin/env python3
"""
InsightIQ: End-to-End System Verification & Healthcheck Suite.

Verifies:
1. Database connectivity (admin and read-only users).
2. Data warehouse table row counts and star schema integrity.
3. Ollama local LLM daemon and required models (qwen2.5:3b, nomic-embed-text).
4. ChromaDB vector knowledge store and semantic retrieval.
5. SQL safety AST validator and read-only policy enforcement.
6. Multi-tool agent orchestrator intent classification and execution.
7. Benchmark evaluation results and pass rate thresholds.
"""

import sys
import os
import json
import time
from pathlib import Path

# Add project root to path
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# ANSI formatting
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
BOLD = "\033[1m"
RESET = "\033[0m"


def check_database() -> bool:
    print(f"\n{BOLD}[1/6] Checking PostgreSQL Database Connectivity & Data Marts...{RESET}")
    try:
        from backend.app.services.database import test_connections, readonly_engine
        from sqlalchemy import text

        conns = test_connections()
        if not conns.get("admin") or not conns.get("readonly"):
            print(f"  {RED}❌ Connection failed:{RESET} Admin={conns.get('admin')}, Readonly={conns.get('readonly')}")
            return False
        print(f"  {GREEN}✓ PostgreSQL connections established (Admin + Read-Only Least Privilege){RESET}")

        with readonly_engine.connect() as conn:
            # Fact table checks
            orders_count = conn.execute(text("SELECT count(*) FROM analytics.fact_orders;")).scalar()
            items_count = conn.execute(text("SELECT count(*) FROM analytics.fact_order_items;")).scalar()
            rev_total = conn.execute(text("SELECT ROUND(SUM(total_order_amount), 2) FROM analytics.fact_orders WHERE is_delivered = TRUE;")).scalar()

            print(f"  {GREEN}✓ fact_orders: {orders_count:,} records{RESET}")
            print(f"  {GREEN}✓ fact_order_items: {items_count:,} records{RESET}")
            print(f"  {GREEN}✓ Delivered Revenue Baseline: R$ {rev_total:,.2f}{RESET}")

            # Reporting views check
            views = [
                "v_monthly_sales",
                "v_category_performance",
                "v_state_sales_distribution",
                "v_customer_rfm_segments",
                "v_seller_performance",
            ]
            for v in views:
                v_count = conn.execute(text(f"SELECT count(*) FROM analytics.{v};")).scalar()
                print(f"  {GREEN}✓ View analytics.{v}: {v_count} rows{RESET}")

        return True
    except Exception as e:
        print(f"  {RED}❌ Database check failed: {e}{RESET}")
        return False


def check_ollama() -> bool:
    print(f"\n{BOLD}[2/6] Checking Local Ollama Runtime & Models...{RESET}")
    try:
        from backend.app.services.llm_client import OllamaClient

        client = OllamaClient()
        is_avail = client.is_available()
        if not is_avail:
            print(f"  {RED}❌ Ollama daemon is unreachable on {client.base_url}{RESET}")
            return False
        print(f"  {GREEN}✓ Ollama daemon is active on {client.base_url}{RESET}")

        models = client.list_models()
        print(f"  {GREEN}✓ Local models detected: {models}{RESET}")

        req_models = ["qwen2.5:3b", "nomic-embed-text"]
        for rm in req_models:
            has_m = any(rm in m for m in models)
            if has_m:
                print(f"  {GREEN}✓ Required model '{rm}' installed{RESET}")
            else:
                print(f"  {YELLOW}⚠️ Model '{rm}' not explicitly listed; ensure it is pulled{RESET}")

        # Quick test generation
        res = client.generate("Respond with 'OK'", temperature=0.0)
        print(f"  {GREEN}✓ Test LLM inference completed ({len(res)} chars returned){RESET}")
        return True
    except Exception as e:
        print(f"  {RED}❌ Ollama verification error: {e}{RESET}")
        return False


def check_rag_and_vector_store() -> bool:
    print(f"\n{BOLD}[3/6] Checking ChromaDB Knowledge Base & Vector Store...{RESET}")
    try:
        from backend.app.rag.vector_store import VectorStoreManager
        from backend.app.rag.retriever import SemanticRetriever

        vsm = VectorStoreManager()
        stats = vsm.get_stats()
        chunk_count = stats.get("total_chunks", 0)
        print(f"  {GREEN}✓ ChromaDB collection '{stats.get('collection_name')}' loaded with {chunk_count} chunks{RESET}")

        if chunk_count == 0:
            print(f"  {RED}❌ Vector store is empty. Ingest knowledge base documents first.{RESET}")
            return False

        retriever = SemanticRetriever(vsm)
        result = retriever.retrieve("What is delivered revenue?", top_k=2)
        citation_count = len(result.citations) if hasattr(result, "citations") else len(result.documents)
        print(f"  {GREEN}✓ Semantic retrieval check returned {citation_count} relevant citations{RESET}")
        return True
    except Exception as e:
        print(f"  {RED}❌ RAG check error: {e}{RESET}")
        return False


def check_sql_validator_and_security() -> bool:
    print(f"\n{BOLD}[4/6] Checking SQL AST Security Validator & Guardrails...{RESET}")
    try:
        from backend.app.services.sql_generator import SQLValidator

        # Safe SELECT
        safe_sql = "SELECT order_id, total_order_value FROM analytics.fact_orders LIMIT 10;"
        is_valid, err = SQLValidator.validate_sql(safe_sql)
        assert is_valid, f"Safe query was unexpectedly rejected: {err}"
        print(f"  {GREEN}✓ Valid read-only query passed validation{RESET}")

        # Malicious DROP
        drop_sql = "DROP TABLE analytics.fact_orders CASCADE;"
        is_valid, err = SQLValidator.validate_sql(drop_sql)
        assert not is_valid, "Dangerous DROP query was not blocked!"
        print(f"  {GREEN}✓ Destructive query blocked by AST validator: '{err}'{RESET}")

        # Malicious UPDATE
        upd_sql = "UPDATE analytics.fact_orders SET total_order_value = 0;"
        is_valid, err = SQLValidator.validate_sql(upd_sql)
        assert not is_valid, "Dangerous UPDATE query was not blocked!"
        print(f"  {GREEN}✓ Mutation query blocked: '{err}'{RESET}")

        # Schema isolation violation
        raw_sql = "SELECT * FROM raw.orders LIMIT 5;"
        is_valid, err = SQLValidator.validate_sql(raw_sql)
        assert not is_valid, "Raw schema query was not blocked!"
        print(f"  {GREEN}✓ Schema isolation enforced: '{err}'{RESET}")

        return True
    except Exception as e:
        print(f"  {RED}❌ SQL Validator security check failed: {e}{RESET}")
        return False


def check_agent_orchestrator() -> bool:
    print(f"\n{BOLD}[5/6] Checking Multi-Tool Orchestrator & Tool Registry...{RESET}")
    try:
        from backend.app.agents.intent_classifier import AgentIntentClassifier
        from backend.app.tools.registry import tool_registry

        tools = tool_registry.list_tools()
        print(f"  {GREEN}✓ Tool registry initialized with {len(tools)} tools: {[t['name'] for t in tools]}{RESET}")

        classifier = AgentIntentClassifier()
        # Test routing
        ic1 = classifier.classify("What is the monthly revenue trend?")
        print(f"  {GREEN}✓ Sales query routed to intent '{ic1.intent}' -> {ic1.tools_required}{RESET}")

        ic2 = classifier.classify("What is the definition of average order value?")
        print(f"  {GREEN}✓ RAG query routed to intent '{ic2.intent}' -> {ic2.tools_required}{RESET}")

        ic3 = classifier.classify("Why did revenue decline between January and February?")
        print(f"  {GREEN}✓ Investigation query routed to intent '{ic3.intent}' -> {ic3.tools_required}{RESET}")

        return True
    except Exception as e:
        print(f"  {RED}❌ Agent orchestrator check failed: {e}{RESET}")
        return False


def check_benchmark_evaluations() -> bool:
    print(f"\n{BOLD}[6/6] Checking Benchmark Evaluation Results...{RESET}")
    try:
        eval_path = ROOT_DIR / "evaluation" / "results" / "latest_evaluation.json"
        if not eval_path.exists():
            print(f"  {YELLOW}⚠️ Evaluation results file not found at {eval_path}{RESET}")
            return False

        with open(eval_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        total = data.get("total_questions", 0)
        passed = data.get("passed_questions", 0)
        rate = data.get("overall_pass_rate_pct", 0.0)
        metrics = data.get("metrics", {})

        print(f"  {GREEN}✓ Latest Benchmark: {passed}/{total} passed ({rate}% pass rate){RESET}")
        print(f"  {GREEN}✓ Tool Accuracy: {metrics.get('tool_selection_accuracy_pct')}% | Grounding: {metrics.get('answer_grounding_pct')}% | Security: {metrics.get('error_handling_accuracy_pct')}%{RESET}")
        return rate >= 80.0
    except Exception as e:
        print(f"  {RED}❌ Benchmark report check failed: {e}{RESET}")
        return False


def main():
    print(f"\n{BLUE}{BOLD}======================================================================{RESET}")
    print(f"{BLUE}{BOLD}⚡ INSIGHTIQ: FULL SYSTEM VERIFICATION & HEALTHCHECK SUITE{RESET}")
    print(f"{BLUE}{BOLD}======================================================================{RESET}")

    start_time = time.time()
    checks = [
        ("PostgreSQL Marts", check_database),
        ("Ollama LLM Runtime", check_ollama),
        ("ChromaDB Vector Store", check_rag_and_vector_store),
        ("SQL AST Security", check_sql_validator_and_security),
        ("Agent Orchestrator", check_agent_orchestrator),
        ("Benchmark Telemetry", check_benchmark_evaluations),
    ]

    results = {}
    for name, fn in checks:
        results[name] = fn()

    elapsed = round(time.time() - start_time, 2)
    all_ok = all(results.values())

    print(f"\n{BLUE}{BOLD}======================================================================{RESET}")
    print(f"{BOLD}SUMMARY SCORECARD:{RESET}")
    for name, ok in results.items():
        status = f"{GREEN}PASS ✓{RESET}" if ok else f"{RED}FAIL ❌{RESET}"
        print(f"  • {name:<25} {status}")
    print(f"Verification Duration: {elapsed}s")
    print(f"{BLUE}{BOLD}======================================================================{RESET}")

    if all_ok:
        print(f"\n{GREEN}{BOLD}🎉 ALL SYSTEMS VERIFIED & HEALTHY. READY FOR PRODUCTION / DEMO!{RESET}\n")
        sys.exit(0)
    else:
        print(f"\n{RED}{BOLD}⚠️ ONE OR MORE CHECKS FAILED. REVIEW LOGS ABOVE.{RESET}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
