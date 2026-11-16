"""
Knowledge Base Indexer and Pipeline CLI for InsightIQ.

Orchestrates:
1. Loading markdown documents from knowledge_base/
2. Semantic chunking with section preservation
3. Generating 768-dim embeddings via nomic-embed-text
4. Indexing into persistent ChromaDB storage
"""

import sys
import logging
import argparse
from typing import Dict, Any

from backend.app.rag.config import (
    KNOWLEDGE_BASE_DIR,
    CHROMA_PERSIST_DIRECTORY,
    CHROMA_COLLECTION_NAME,
)
from backend.app.rag.document_loader import KnowledgeBaseLoader
from backend.app.rag.text_splitter import MarkdownTextSplitter
from backend.app.rag.embeddings import get_embedding_function
from backend.app.rag.vector_store import VectorStoreManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("rag_indexer")


class KnowledgeBaseIndexer:
    """End-to-end indexing pipeline manager."""

    def __init__(self, rebuild: bool = False):
        self.rebuild = rebuild
        self.loader = KnowledgeBaseLoader(KNOWLEDGE_BASE_DIR)
        self.splitter = MarkdownTextSplitter()
        self.embeddings = get_embedding_function()
        self.vector_store = VectorStoreManager(
            persist_directory=CHROMA_PERSIST_DIRECTORY,
            collection_name=CHROMA_COLLECTION_NAME,
            embeddings=self.embeddings,
        )

    def run(self) -> Dict[str, Any]:
        """Executes the full indexing workflow."""
        logger.info("=" * 60)
        logger.info("Starting InsightIQ Knowledge Base Indexing Pipeline")
        logger.info(f"Knowledge Base Source: {KNOWLEDGE_BASE_DIR}")
        logger.info(f"Vector DB Destination: {CHROMA_PERSIST_DIRECTORY}")
        logger.info(f"Embedding Model: {self.embeddings.model}")
        logger.info("=" * 60)

        # 1. Validation & Loading
        validation = self.loader.validate_knowledge_base()
        missing = [f for f, exists in validation.items() if not exists]
        if missing:
            raise FileNotFoundError(f"Missing required knowledge base documents: {missing}")

        documents = self.loader.load_documents()
        logger.info(f"Loaded {len(documents)} source markdown documents.")

        # 2. Semantic Chunking
        chunks = self.splitter.split_documents(documents)
        logger.info(f"Split into {len(chunks)} contextual chunks.")

        # 3. Vector DB Reset if requested
        if self.rebuild:
            logger.info("Rebuild requested: clearing existing ChromaDB collection...")
            self.vector_store.reset()

        # Check existing count
        current_count = self.vector_store.count()
        if current_count > 0 and not self.rebuild:
            logger.info(f"Vector store already contains {current_count} documents. Re-indexing with reset...")
            self.vector_store.reset()

        # 4. Vector Embedding and Indexing
        logger.info("Embedding chunks via Ollama nomic-embed-text and saving to ChromaDB...")
        added_count = self.vector_store.add_documents(chunks)
        final_count = self.vector_store.count()

        logger.info("=" * 60)
        logger.info(f"Indexing Complete! Total vectors indexed: {final_count}")
        logger.info("=" * 60)

        # 5. Sanity Verification Query
        test_query = "What is the definition of average order value?"
        logger.info(f"Running sanity retrieval test for query: '{test_query}'")
        results = self.vector_store.similarity_search_with_scores(test_query, k=1)
        if results:
            doc, score = results[0]
            logger.info(f"Sanity Check Top Match: {doc.metadata.get('source')} (Score: {score:.4f})")
            logger.info(f"Snippet: {doc.page_content[:150]}...")

        return {
            "source_documents": len(documents),
            "total_chunks": len(chunks),
            "indexed_vectors": final_count,
            "status": "success",
        }


def main():
    parser = argparse.ArgumentParser(description="InsightIQ Knowledge Base Vector Indexer")
    parser.add_argument("--rebuild", action="store_true", help="Force wipe and rebuild of ChromaDB collection")
    args = parser.parse_args()

    indexer = KnowledgeBaseIndexer(rebuild=args.rebuild)
    try:
        indexer.run()
    except Exception as e:
        logger.error(f"Indexing pipeline failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
