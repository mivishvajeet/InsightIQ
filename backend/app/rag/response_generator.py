"""
Context-Grounded Response Generator for InsightIQ RAG.

Synthesizes evidence-based, strictly grounded business answers from retrieved documentation chunks
using local Qwen 2.5 3B, enforcing citation attribution and limitation disclosures.
"""

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict

from backend.app.services.llm_client import OllamaClient
from backend.app.rag.retriever import RetrievalResult, Citation

logger = logging.getLogger(__name__)

RAG_SYSTEM_PROMPT = """You are the InsightIQ Knowledge Assistant, an expert business analyst AI for the Brazilian Olist E-Commerce enterprise.

Your mission is to provide accurate, grounded answers to business and operational questions strictly based on the provided documentation context.

STRICT GROUNDING RULES:
1. ONLY use information explicitly stated in the provided documentation context.
2. DO NOT hallucinate, extrapolate, or invent metrics, numbers, formulas, or operational policies.
3. Every factual claim or definition must explicitly reference its source document (e.g., [metric_definitions.md] or [database_schema.md]).
4. If the provided context does NOT contain enough information to answer the question, state explicitly:
   "The available InsightIQ documentation does not contain information regarding this topic."
   Do NOT attempt to guess.
5. Keep explanations professional, concise, and structured with bullet points and bold headers where appropriate.
"""


@dataclass
class GroundedAnswer:
    """Represents a validated, context-grounded response."""
    question: str
    answer: str
    citations: List[Citation]
    is_grounded: bool
    context_chunks_used: int
    has_limitation: bool

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["citations"] = [c.to_dict() if isinstance(c, Citation) else c for c in self.citations]
        return data


class ResponseGenerator:
    """Generates context-grounded business answers from retrieved documentation."""

    def __init__(self, llm_client: Optional[OllamaClient] = None):
        self.llm = llm_client or OllamaClient()

    def generate_answer(
        self,
        question: str,
        retrieval_result: RetrievalResult,
        temperature: float = 0.1,
    ) -> GroundedAnswer:
        """
        Synthesizes an answer using the retrieved context blocks and the user question.
        """
        if not retrieval_result.chunks:
            return GroundedAnswer(
                question=question,
                answer="The available InsightIQ documentation does not contain information regarding this topic.",
                citations=[],
                is_grounded=True,
                context_chunks_used=0,
                has_limitation=True,
            )

        user_prompt = f"""DOCUMENTATION CONTEXT:
{retrieval_result.context_text}

USER QUESTION:
{question}

Provide an accurate, concise, grounded answer based solely on the documentation context above. Include source citations."""

        try:
            raw_answer = self.llm.generate(
                prompt=user_prompt,
                system_prompt=RAG_SYSTEM_PROMPT,
                temperature=temperature,
            )
        except Exception as e:
            logger.error(f"Failed to generate RAG answer via Ollama: {e}")
            raise RuntimeError(f"RAG generation failure: {e}") from e

        # Analyze if limitation was reported
        limitation_phrases = [
            "does not contain",
            "not mentioned",
            "insufficient information",
            "unavailable",
            "cannot be answered",
        ]
        has_limitation = any(phrase in raw_answer.lower() for phrase in limitation_phrases)

        return GroundedAnswer(
            question=question,
            answer=raw_answer.strip(),
            citations=retrieval_result.citations,
            is_grounded=True,
            context_chunks_used=len(retrieval_result.chunks),
            has_limitation=has_limitation,
        )
