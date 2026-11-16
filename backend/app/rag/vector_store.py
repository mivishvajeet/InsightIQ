"""
ChromaDB Vector Store Manager for InsightIQ.

Manages persistent on-disk embedding storage, collection lifecycle, similarity searches,
and score normalization using ChromaDB and LangChain.
"""

import os
import logging
import warnings
from pathlib import Path
from typing import List, Tuple, Dict, Any, Optional

# Suppress deprecation warnings from langchain_community
warnings.filterwarnings("ignore", category=DeprecationWarning)

import chromadb
from chromadb.config import Settings
from langchain_core.documents import Document
from langchain_community.vectorstores import Chroma

from backend.app.rag.config import (
    CHROMA_PERSIST_DIRECTORY,
    CHROMA_COLLECTION_NAME,
    DEFAULT_TOP_K,
)
from backend.app.rag.embeddings import InsightIQEmbeddings, get_embedding_function

logger = logging.getLogger(__name__)


class VectorStoreManager:
    """
    Manages vector indexing and semantic retrieval in local ChromaDB storage.
    """

    def __init__(
        self,
        persist_directory: Optional[Path] = None,
        collection_name: str = CHROMA_COLLECTION_NAME,
        embeddings: Optional[InsightIQEmbeddings] = None,
    ):
        self.persist_directory = Path(persist_directory) if persist_directory else CHROMA_PERSIST_DIRECTORY
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        self.collection_name = collection_name
        self.embeddings = embeddings or get_embedding_function()

        # Initialize persistent chromadb client
        self._chroma_client = chromadb.PersistentClient(
            path=str(self.persist_directory.resolve()),
            settings=Settings(anonymized_telemetry=False, is_persistent=True),
        )

        # Initialize LangChain Chroma wrapper
        self.vector_store = Chroma(
            client=self._chroma_client,
            collection_name=self.collection_name,
            embedding_function=self.embeddings,
        )

    def count(self) -> int:
        """Returns the total number of indexed vectors in the active collection."""
        try:
            collection = self._chroma_client.get_collection(self.collection_name)
            return collection.count()
        except Exception:
            return 0

    def get_stats(self) -> Dict[str, Any]:
        """Returns collection metadata, persist directory, and document count."""
        return {
            "collection_name": self.collection_name,
            "persist_directory": str(self.persist_directory.resolve()),
            "total_chunks": self.count(),
            "embedding_model": self.embeddings.model,
        }

    def reset(self) -> None:
        """Clears the collection completely to allow fresh re-indexing."""
        try:
            self._chroma_client.delete_collection(self.collection_name)
            logger.info(f"Deleted collection '{self.collection_name}' from ChromaDB.")
        except Exception as e:
            logger.info(f"Collection '{self.collection_name}' did not exist or could not be deleted: {e}")

        # Re-initialize collection
        self.vector_store = Chroma(
            client=self._chroma_client,
            collection_name=self.collection_name,
            embedding_function=self.embeddings,
        )

    def add_documents(self, documents: List[Document]) -> int:
        """
        Embeds and stores a list of chunked Document objects.
        Returns the number of documents added.
        """
        if not documents:
            return 0

        # Extract IDs from metadata if available
        ids = [doc.metadata.get("chunk_id") for doc in documents]
        if any(i is None for i in ids):
            ids = None

        self.vector_store.add_documents(documents=documents, ids=ids)
        total = self.count()
        logger.info(f"Successfully indexed {len(documents)} chunks. Collection total: {total}")
        return len(documents)

    def similarity_search(
        self,
        query: str,
        k: int = DEFAULT_TOP_K,
        filter_dict: Optional[Dict[str, Any]] = None,
    ) -> List[Document]:
        """
        Performs cosine/L2 semantic similarity search.
        """
        return self.vector_store.similarity_search(query=query, k=k, filter=filter_dict)

    def similarity_search_with_scores(
        self,
        query: str,
        k: int = DEFAULT_TOP_K,
        filter_dict: Optional[Dict[str, Any]] = None,
    ) -> List[Tuple[Document, float]]:
        """
        Performs similarity search returning (Document, distance/score) tuples.
        """
        return self.vector_store.similarity_search_with_score(query=query, k=k, filter=filter_dict)
