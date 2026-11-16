"""
Ollama Embeddings Service for InsightIQ.

Integrates Ollama's local embedding runtime (nomic-embed-text) with LangChain and ChromaDB.
Provides robust connection checks, query embedding, and batch document embedding.
"""

import logging
from typing import List, Optional
import requests
from langchain_core.embeddings import Embeddings
from langchain_ollama import OllamaEmbeddings

from backend.app.rag.config import OLLAMA_BASE_URL, EMBEDDING_MODEL

logger = logging.getLogger(__name__)

EXPECTED_EMBEDDING_DIM = 768


class InsightIQEmbeddings(Embeddings):
    """
    Embedding provider backed by local Ollama nomic-embed-text model.
    Implements the standard LangChain Embeddings interface.
    """

    def __init__(
        self,
        base_url: str = OLLAMA_BASE_URL,
        model: str = EMBEDDING_MODEL,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self._langchain_embeddings = OllamaEmbeddings(
            base_url=self.base_url,
            model=self.model,
        )

    def is_available(self) -> bool:
        """Checks if the Ollama embedding service is operational."""
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=3)
            if resp.status_code == 200:
                models = [m.get("name") for m in resp.json().get("models", [])]
                return any(self.model in m for m in models)
            return False
        except Exception:
            return False

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Generates embedding vectors for a batch of text chunks."""
        if not texts:
            return []
        try:
            embeddings = self._langchain_embeddings.embed_documents(texts)
            if embeddings and len(embeddings[0]) != EXPECTED_EMBEDDING_DIM:
                logger.warning(
                    f"Embedding dimension mismatch: expected {EXPECTED_EMBEDDING_DIM}, got {len(embeddings[0])}"
                )
            return embeddings
        except Exception as e:
            logger.error(f"Failed to embed documents with Ollama ({self.model}): {e}")
            raise RuntimeError(f"Ollama embedding error: {e}") from e

    def embed_query(self, text: str) -> List[float]:
        """Generates an embedding vector for a single search query."""
        try:
            return self._langchain_embeddings.embed_query(text)
        except Exception as e:
            logger.error(f"Failed to embed query with Ollama ({self.model}): {e}")
            raise RuntimeError(f"Ollama query embedding error: {e}") from e


def get_embedding_function(
    base_url: str = OLLAMA_BASE_URL,
    model: str = EMBEDDING_MODEL,
) -> InsightIQEmbeddings:
    """Factory function for retrieving the configured embedding instance."""
    return InsightIQEmbeddings(base_url=base_url, model=model)
