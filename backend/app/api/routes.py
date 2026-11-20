"""
FastAPI Routes for InsightIQ Analytics & AI Agent endpoints.
"""

import time
import json
from pathlib import Path
from typing import Dict, Any, List
from starlette.responses import StreamingResponse
from fastapi import APIRouter, HTTPException
from backend.app.api.schemas import (
    QueryRequest,
    QueryResponse,
    ExecutiveKPIResponse,
    RAGRetrieveRequest,
    RAGRetrieveResponse,
    RAGQueryRequest,
    RAGQueryResponse,
    RAGStatusResponse,
    AgentQueryRequest,
    AgentQueryResponse,
    InvestigationRequest,
    InvestigationResponse,
    ExecutiveReportResponse,
    EvaluationRunRequest,
    EvaluationScorecardResponse,
)
from backend.app.services.kpi_service import KPIService
from backend.app.services.anomaly_detector import AnomalyDetector
from backend.app.services.correlation_analyzer import CorrelationAnalyzer
from backend.app.services.customer_analytics import CustomerAnalyticsService
from backend.app.services.sql_generator import SQLGenerator
from backend.app.rag.pipeline import rag_pipeline
from backend.app.agents.orchestrator import orchestrator_agent
from backend.app.tools.registry import tool_registry
from backend.app.reporting.report_generator import ReportGeneratorService

router = APIRouter(prefix="/api", tags=["Analytics & AI"])
sql_generator = SQLGenerator()


@router.get("/kpi/summary", response_model=ExecutiveKPIResponse)
def get_kpi_summary():
    """Returns top-level executive business performance KPIs."""
    try:
        data = KPIService.get_executive_summary()
        return ExecutiveKPIResponse(**data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/kpi/monthly")
def get_monthly_growth():
    """Returns monthly sales volume and MoM growth percentages."""
    try:
        df = KPIService.get_monthly_growth_trend()
        # Replace NaN with 0.0 or None for valid JSON serialization
        df = df.fillna(0.0)
        return df.to_dict(orient="records")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/anomalies/revenue")
def get_revenue_anomalies():
    """Returns detected revenue spikes and drops via Z-score / IQR."""
    try:
        return AnomalyDetector.get_top_anomalies(10)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/correlations/delivery")
def get_delivery_correlation():
    """Returns correlation between transit delays and customer review scores."""
    try:
        return CorrelationAnalyzer.analyze_delivery_vs_satisfaction()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/customers/rfm")
def get_customer_rfm():
    """Returns customer RFM segment breakdown."""
    try:
        df = CustomerAnalyticsService.get_rfm_summary()
        return df.to_dict(orient="records")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sql/query", response_model=QueryResponse)
def query_natural_language(req: QueryRequest):
    """
    Translates a natural-language question into validated SQL and executes it against PostgreSQL.
    """
    start_time = time.time()
    try:
        sql = sql_generator.generate_sql(req.question)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM generation failed: {e}")

    explanation = ""
    data_records: List[Dict[str, Any]] = []
    columns: List[str] = []
    row_count = 0
    error = None

    if req.execute:
        df, error = sql_generator.execute_query(sql)
        if error is None:
            data_records = df.to_dict(orient="records")
            columns = list(df.columns)
            row_count = len(df)
            explanation = sql_generator.explain_query(req.question, sql)

    elapsed = round(time.time() - start_time, 3)

    return QueryResponse(
        question=req.question,
        sql=sql,
        explanation=explanation,
        execution_time_seconds=elapsed,
        row_count=row_count,
        columns=columns,
        data=data_records,
        error=error,
    )


@router.get("/rag/status", response_model=RAGStatusResponse)
def get_rag_status():
    """Returns vector store collection metrics and embedding engine readiness."""
    try:
        return rag_pipeline.get_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rag/retrieve", response_model=RAGRetrieveResponse)
def retrieve_knowledge_context(req: RAGRetrieveRequest):
    """
    Performs vector similarity search against ChromaDB, returning retrieved chunks and citations.
    """
    try:
        res = rag_pipeline.retrieve(
            query=req.query,
            top_k=req.top_k,
            category=req.category,
        )
        return RAGRetrieveResponse(
            query=res.query,
            total_found=res.total_found,
            citations=[c.to_dict() for c in res.citations],
            context_text=res.context_text,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Retrieval error: {e}")


@router.post("/rag/query", response_model=RAGQueryResponse)
def ask_knowledge_base(req: RAGQueryRequest):
    """
    Synthesizes a context-grounded business answer with structured citations using Qwen 2.5 3B.
    """
    try:
        answer = rag_pipeline.answer_question(
            question=req.question,
            top_k=req.top_k,
            category=req.category,
            temperature=req.temperature,
        )
        return RAGQueryResponse(
            question=answer.question,
            answer=answer.answer,
            citations=[c.to_dict() for c in answer.citations],
            is_grounded=answer.is_grounded,
            context_chunks_used=answer.context_chunks_used,
            has_limitation=answer.has_limitation,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"RAG query error: {e}")


@router.get("/agent/tools")
def list_registered_agent_tools():
    """Lists all specialized tools available to the orchestrator agent."""
    return tool_registry.list_tools()


@router.post("/agent/query", response_model=AgentQueryResponse)
def execute_agent_query(req: AgentQueryRequest):
    """
    Executes the full agentic multi-tool workflow: intent classification,
    tool execution (SQL, RAG, Python), step tracing, and evidence synthesis.
    """
    try:
        result = orchestrator_agent.run(
            question=req.question,
            mode_override=req.mode_override,
            top_k=req.top_k,
            session_id=req.session_id or "default_session",
        )
        return AgentQueryResponse(**result.to_dict())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent orchestration failed: {e}")


@router.post("/agent/stream")
def stream_agent_query(req: AgentQueryRequest):
    """
    Streams agent synthesis tokens in real-time using Server-Sent Events (SSE).
    Yields 'steps', incremental 'token' chunks, and terminal 'done' events.
    """
    def event_generator():
        try:
            session = req.session_id or "default_session"
            result = orchestrator_agent.run(
                question=req.question,
                mode_override=req.mode_override,
                top_k=req.top_k,
                session_id=session,
            )

            # Step 1: Yield steps event
            steps_payload = {
                "steps": result.execution_steps,
                "intent": result.intent,
                "tools": result.tools_used,
                "sql": result.sql_query,
                "row_count": len(result.data_table),
            }
            yield f"event: steps\ndata: {json.dumps(steps_payload)}\n\n"

            # Step 2: Stream tokens incrementally
            words = result.final_answer.split(" ")
            for i, w in enumerate(words):
                tok = w + (" " if i < len(words) - 1 else "")
                yield f"event: token\ndata: {json.dumps({'token': tok})}\n\n"
                time.sleep(0.015)

            # Step 3: Yield terminal completed event
            yield f"event: done\ndata: {json.dumps(result.to_dict())}\n\n"
        except Exception as e:
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")



@router.post("/investigation/run", response_model=InvestigationResponse)
def run_business_investigation(req: InvestigationRequest):
    """
    Executes a structured deep-dive business investigation across revenue, satisfaction, sellers, or routes.
    """
    try:
        out = tool_registry.execute_tool(
            "business_investigation_tool",
            investigation_type=req.investigation_type,
            params=req.params,
        )
        return InvestigationResponse(**out)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Investigation failed: {e}")


@router.get("/reports/executive", response_model=ExecutiveReportResponse)
def get_executive_report():
    """Compiles and returns the comprehensive Executive Business Performance Report."""
    try:
        data = ReportGeneratorService.generate_executive_business_report()
        return ExecutiveReportResponse(**data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Report compilation failed: {e}")


@router.get("/evaluation/summary", response_model=EvaluationScorecardResponse)
def get_evaluation_summary():
    """Retrieves the latest benchmark evaluation scorecard and metrics."""
    result_path = Path("evaluation/results/latest_evaluation.json")
    if not result_path.exists():
        raise HTTPException(status_code=404, detail="No evaluation results found. Run evaluation first.")

    try:
        with open(result_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return EvaluationScorecardResponse(**data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read evaluation report: {e}")


@router.post("/evaluation/run", response_model=EvaluationScorecardResponse)
def run_evaluation_benchmark(req: EvaluationRunRequest):
    """Executes the benchmark evaluation on demand and returns the updated scorecard."""
    try:
        from evaluation.evaluator import BenchmarkEvaluator
        evaluator = BenchmarkEvaluator()
        report = evaluator.run_benchmark(category=req.category, limit=req.limit)
        return EvaluationScorecardResponse(**report)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Evaluation execution failed: {e}")





