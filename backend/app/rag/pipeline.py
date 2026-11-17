"""
End-to-End RAG Pipeline Service for InsightIQ.

Unifies vector retrieval, relevance scoring, and context-grounded response generation
into a cohesive service for API endpoints, tools, and UI components.
"""

import logging
from typing import Dict, Any, Optional

from backend.app.rag.vector_store import VectorStoreManager
from backend.app.rag.retriever import SemanticRetriever, RetrievalResult
from backend.app.rag.response_generator import ResponseGenerator, GroundedAnswer
from backend.app.services.llm_client import OllamaClient

logger = logging.getLogger(__name__)


class RAGPipeline:
    """High-level facade for the InsightIQ RAG retrieval and Q&A subsystem."""

    def __init__(
        self,
        retriever: Optional[SemanticRetriever] = None,
        generator: Optional[ResponseGenerator] = None,
    ):
        self.retriever = retriever or SemanticRetriever()
        self.generator = generator or ResponseGenerator()

    def get_status(self) -> Dict[str, Any]:
        """Provides status of the vector store and embedding service."""
        stats = self.retriever.vector_store.get_stats()
        llm_ready = self.generator.llm.is_available()
        return {
            "status": "ready" if stats["total_chunks"] > 0 and llm_ready else "degraded",
            "vector_store": stats,
            "llm_available": llm_ready,
        }

    def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        category: Optional[str] = None,
    ) -> RetrievalResult:
        """Retrieves raw context chunks and citations without LLM synthesis."""
        return self.retriever.retrieve(query=query, top_k=top_k, category=category)

    def answer_question(
        self,
        question: str,
        top_k: Optional[int] = None,
        category: Optional[str] = None,
        temperature: float = 0.1,
    ) -> GroundedAnswer:
        """
        Executes end-to-end RAG: retrieves relevant documentation and generates a grounded response.
        """
        logger.info(f"RAG answering question: '{question}'")
        retrieval_result = self.retrieve(query=question, top_k=top_k, category=category)
        return self.generator.generate_answer(
            question=question,
            retrieval_result=retrieval_result,
            temperature=temperature,
        )


# Singleton instance for application-wide use
rag_pipeline = RAGPipeline()

