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


class CitationModel(BaseModel):
    source: str
    title: str
    section: str
    chunk_id: str
    relevance_score: float
    snippet: str


class RAGRetrieveRequest(BaseModel):
    query: str = Field(..., description="Query for semantic knowledge retrieval", json_schema_extra={"example": "What is the definition of average order value?"})
    top_k: int = Field(4, ge=1, le=10, description="Number of context chunks to retrieve")
    category: Optional[str] = Field(None, description="Optional category filter (e.g., metrics, schema, logistics)")


class RAGRetrieveResponse(BaseModel):
    query: str
    total_found: int
    citations: List[CitationModel]
    context_text: str


class RAGQueryRequest(BaseModel):
    question: str = Field(..., description="Business question for grounded RAG answering", json_schema_extra={"example": "How is customer retention calculated?"})
    top_k: int = Field(4, ge=1, le=10, description="Number of context chunks to retrieve")
    category: Optional[str] = None
    temperature: float = Field(0.1, ge=0.0, le=1.0)


class RAGQueryResponse(BaseModel):
    question: str
    answer: str
    citations: List[CitationModel]
    is_grounded: bool
    context_chunks_used: int
    has_limitation: bool


class RAGStatusResponse(BaseModel):
    status: str
    vector_store: Dict[str, Any]
    llm_available: bool

