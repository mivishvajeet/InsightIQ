"""
Semantic Retriever for InsightIQ Knowledge Base.

Performs vector similarity search against ChromaDB, computes normalized relevance scores,
extracts structured citations, and packages grounded context for LLM response generation.
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict

from langchain_core.documents import Document

from backend.app.rag.config import (
    DEFAULT_TOP_K,
    SIMILARITY_SCORE_THRESHOLD,
    CHROMA_PERSIST_DIRECTORY,
    CHROMA_COLLECTION_NAME,
)
from backend.app.rag.vector_store import VectorStoreManager

logger = logging.getLogger(__name__)


@dataclass
class Citation:
    """Structured citation metadata for retrieved context grounding."""
    source: str
    title: str
    section: str
    chunk_id: str
    relevance_score: float
    snippet: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RetrievalResult:
    """Standardized retrieval result containing context chunks and verified citations."""
    query: str
    chunks: List[Document]
    citations: List[Citation]
    total_found: int

    @property
    def context_text(self) -> str:
        """Combines all retrieved chunks into a clean, numbered context block for LLM prompts."""
        if not self.chunks:
            return "No relevant business documentation found in knowledge base."

        formatted_blocks = []
        for i, doc in enumerate(self.chunks, 1):
            source = doc.metadata.get("source", "unknown")
            section = doc.metadata.get("section", "General")
            formatted_blocks.append(
                f"[Document {i} | Source: {source} | Section: {section}]\n{doc.page_content}"
            )
        return "\n\n---\n\n".join(formatted_blocks)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "total_found": self.total_found,
            "citations": [c.to_dict() for c in self.citations],
            "context_text": self.context_text,
        }


class SemanticRetriever:
    """Retrieves grounded domain context from the indexed ChromaDB knowledge base."""

    def __init__(
        self,
        vector_store: Optional[VectorStoreManager] = None,
        default_top_k: int = DEFAULT_TOP_K,
        score_threshold: float = SIMILARITY_SCORE_THRESHOLD,
    ):
        self.vector_store = vector_store or VectorStoreManager(
            persist_directory=CHROMA_PERSIST_DIRECTORY,
            collection_name=CHROMA_COLLECTION_NAME,
        )
        self.default_top_k = default_top_k
        self.score_threshold = score_threshold

    def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        category: Optional[str] = None,
    ) -> RetrievalResult:
        """
        Retrieves top_k relevant documentation chunks and constructs structured citations.
        """
        k = top_k or self.default_top_k
        filter_dict = {"category": category} if category else None

        # Chroma distance: lower is closer. LangChain with_score returns (doc, distance)
        try:
            results_with_scores = self.vector_store.similarity_search_with_scores(
                query=query,
                k=k,
                filter_dict=filter_dict,
            )
        except Exception as e:
            logger.error(f"Vector search failed for query '{query}': {e}")
            return RetrievalResult(query=query, chunks=[], citations=[], total_found=0)

        chunks: List[Document] = []
        citations: List[Citation] = []

        for doc, distance in results_with_scores:
            # Chroma default L2 distance / cosine distance conversion to 0.0 - 1.0 similarity
            # For normalized embeddings, cosine distance d in [0, 2], similarity = 1 - (d / 2)
            similarity = max(0.0, min(1.0, 1.0 - (distance / 2.0)))

            chunks.append(doc)
            citations.append(
                Citation(
                    source=doc.metadata.get("source", "unknown"),
                    title=doc.metadata.get("title", "InsightIQ Docs"),
                    section=doc.metadata.get("section", "General"),
                    chunk_id=doc.metadata.get("chunk_id", ""),
                    relevance_score=round(similarity, 4),
                    snippet=doc.page_content[:200].strip().replace("\n", " ") + "...",
                )
            )

        return RetrievalResult(
            query=query,
            chunks=chunks,
            citations=citations,
            total_found=len(chunks),
        )
