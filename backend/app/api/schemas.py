"""
Pydantic API Schemas for InsightIQ.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = "ok"
    database_connected: bool
    ollama_connected: bool


class QueryRequest(BaseModel):
    question: str = Field(..., description="Natural language business question", json_schema_extra={"example": "What is the monthly revenue trend?"})
    execute: bool = Field(True, description="Whether to execute the generated query against PostgreSQL")


class QueryResponse(BaseModel):
    question: str
    sql: str
    explanation: str
    execution_time_seconds: float
    row_count: int
    columns: List[str]
    data: List[Dict[str, Any]]
    error: Optional[str] = None


class ExecutiveKPIResponse(BaseModel):
    total_revenue: float
    total_gmv: float
    total_freight: float
    total_orders: int
    delivered_orders: int
    aov: float
    unique_customers: int
    repeat_customers: int
    repeat_purchase_rate_pct: float
    avg_review_score: float
    avg_delivery_days: float
    on_time_rate_pct: float
