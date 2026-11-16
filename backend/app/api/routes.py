"""
FastAPI Routes for InsightIQ Analytics & AI Agent endpoints.
"""

import time
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException
from backend.app.api.schemas import (
    QueryRequest,
    QueryResponse,
    ExecutiveKPIResponse,
)
from backend.app.services.kpi_service import KPIService
from backend.app.services.anomaly_detector import AnomalyDetector
from backend.app.services.correlation_analyzer import CorrelationAnalyzer
from backend.app.services.customer_analytics import CustomerAnalyticsService
from backend.app.services.sql_generator import SQLGenerator

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
