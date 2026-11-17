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


class ExecutionStepModel(BaseModel):
    step_number: int
    step_name: str
    tool_name: Optional[str] = None
    description: str
    status: str
    duration_seconds: float


class AgentQueryRequest(BaseModel):
    question: str = Field(..., description="Natural language business question", json_schema_extra={"example": "What is the monthly revenue trend and how is delivered revenue defined?"})
    mode_override: Optional[str] = Field(None, description="Optional tool override: 'sql', 'rag', 'python', 'hybrid', or 'auto'")
    top_k: int = Field(4, ge=1, le=10)


class AgentQueryResponse(BaseModel):
    question: str
    final_answer: str
    intent: str
    tools_used: List[str]
    execution_steps: List[ExecutionStepModel]
    tool_outputs: Dict[str, Any]
    sql_query: Optional[str] = None
    data_table: List[Dict[str, Any]] = []
    columns: List[str] = []
    citations: List[CitationModel] = []
    total_execution_time_seconds: float
    error: Optional[str] = None


class InvestigationRequest(BaseModel):
    investigation_type: str = Field(..., description="Type of investigation: revenue_anomaly, satisfaction_drivers, seller_performance, transit_bottlenecks, underperforming_categories")
    params: Optional[Dict[str, Any]] = None


class InvestigationResponse(BaseModel):
    success: bool
    investigation_type: str
    executive_summary: str
    metrics: Dict[str, Any]
    evidence_data: List[Dict[str, Any]]
    causation_guardrail: str
    recommended_action: str
    execution_time_seconds: float
    error: Optional[str] = None


class ExecutiveReportResponse(BaseModel):
    title: str
    timestamp: str
    metrics: Dict[str, Any]
    markdown: str
    sections: List[str]


class EvaluationRunRequest(BaseModel):
    category: Optional[str] = Field(None, description="Optional category filter (e.g., Sales Analytics, Customer Analytics)")
    limit: Optional[int] = Field(None, ge=1, le=50, description="Optional maximum number of benchmark questions to evaluate")


class EvaluationScorecardResponse(BaseModel):
    timestamp: str
    total_questions: int
    passed_questions: int
    overall_pass_rate_pct: float
    metrics: Dict[str, Any]
    category_breakdown: Dict[str, Dict[str, Any]]
    question_scores: List[Dict[str, Any]]





