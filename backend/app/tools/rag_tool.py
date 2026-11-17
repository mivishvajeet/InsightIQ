"""
RAG Retrieval Tool for InsightIQ Agent.

Retrieves contextual business knowledge, metric definitions, and schema specifications
from ChromaDB with citation references and synthesized grounded answers.
"""

import time
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict

from backend.app.rag.pipeline import rag_pipeline, RAGPipeline
from backend.app.rag.retriever import Citation

logger = logging.getLogger(__name__)


@dataclass
class RAGToolOutput:
    """Structured output from RAG tool execution."""
    success: bool
    query: str
    answer: str
    citations: List[Dict[str, Any]]
    context_text: str
    total_found: int
    is_grounded: bool
    has_limitation: bool
    execution_time_seconds: float
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class RAGRetrievalTool:
    """Agent tool for querying enterprise business documentation and domain knowledge."""

    name: str = "rag_retrieval_tool"
    description: str = (
        "Retrieves business definitions, metric calculations, database schemas, and operational policies "
        "from the knowledge base using semantic vector search with Nomic Embed Text and ChromaDB."
    )

    def __init__(self, pipeline: Optional[RAGPipeline] = None):
        self.pipeline = pipeline or rag_pipeline

    def run(
        self,
        query: str,
        top_k: int = 4,
        category: Optional[str] = None,
        synthesize_answer: bool = True,
    ) -> RAGToolOutput:
        """
        Executes semantic retrieval. If synthesize_answer is True, invokes Qwen 2.5 3B for a grounded answer.
        """
        start_time = time.time()
        logger.info(f"Executing RAGRetrievalTool for: '{query}'")

        try:
            if synthesize_answer:
                res = self.pipeline.answer_question(question=query, top_k=top_k, category=category)
                citations_data = [c.to_dict() if isinstance(c, Citation) else c for c in res.citations]
                # Reconstruct brief context text
                context_blocks = [f"[{c['source']} - {c['section']}]: {c['snippet']}" for c in citations_data]
                context_text = "\n\n".join(context_blocks)

                elapsed = round(time.time() - start_time, 3)
                return RAGToolOutput(
                    success=True,
                    query=query,
                    answer=res.answer,
                    citations=citations_data,
                    context_text=context_text,
                    total_found=len(citations_data),
                    is_grounded=res.is_grounded,
                    has_limitation=res.has_limitation,
                    execution_time_seconds=elapsed,
                    error=None,
                )
            else:
                retrieval = self.pipeline.retrieve(query=query, top_k=top_k, category=category)
                citations_data = [c.to_dict() for c in retrieval.citations]
                elapsed = round(time.time() - start_time, 3)
                return RAGToolOutput(
                    success=True,
                    query=query,
                    answer="",
                    citations=citations_data,
                    context_text=retrieval.context_text,
                    total_found=retrieval.total_found,
                    is_grounded=True,
                    has_limitation=retrieval.total_found == 0,
                    execution_time_seconds=elapsed,
                    error=None,
                )
        except Exception as e:
            logger.error(f"RAGRetrievalTool execution failed: {e}")
            elapsed = round(time.time() - start_time, 3)
            return RAGToolOutput(
                success=False,
                query=query,
                answer="Failed to retrieve knowledge base context.",
                citations=[],
                context_text="",
                total_found=0,
                is_grounded=False,
                has_limitation=True,
                execution_time_seconds=elapsed,
                error=str(e),
            )
