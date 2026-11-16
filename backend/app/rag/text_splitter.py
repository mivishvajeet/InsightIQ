"""
Text Splitter and Chunking Service for InsightIQ Knowledge Base.

Splits loaded markdown documents into semantic, cohesive chunks using RecursiveCharacterTextSplitter
with markdown-aware separators, preserving section contexts, formulas, and metadata.
"""

import re
import logging
from typing import List, Optional
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from backend.app.rag.config import CHUNK_SIZE, CHUNK_OVERLAP

logger = logging.getLogger(__name__)


class MarkdownTextSplitter:
    """Markdown-aware text splitter that preserves headings and section context."""

    def __init__(
        self,
        chunk_size: int = CHUNK_SIZE,
        chunk_overlap: int = CHUNK_OVERLAP,
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            separators=["\n## ", "\n### ", "\n#### ", "\n\n", "\n- ", "\n", " ", ""],
            keep_separator=True,
        )

    def _extract_section(self, text: str) -> Optional[str]:
        """Finds the first markdown heading in the text chunk if available."""
        match = re.search(r"^(?:#{1,4})\s+(.+)$", text, re.MULTILINE)
        if match:
            return match.group(1).strip()
        return None

    def split_documents(self, documents: List[Document]) -> List[Document]:
        """
        Splits a collection of parent documents into enriched chunks with persistent identifiers.
        """
        raw_chunks = self.splitter.split_documents(documents)
        enriched_chunks: List[Document] = []

        # Track per-document chunk indexing
        doc_chunk_counters: dict[str, int] = {}

        for chunk in raw_chunks:
            source = chunk.metadata.get("source", "unknown")
            counter = doc_chunk_counters.get(source, 0)
            doc_chunk_counters[source] = counter + 1

            # Extract section heading
            section = self._extract_section(chunk.page_content)
            if not section:
                section = chunk.metadata.get("title", "General")

            metadata = dict(chunk.metadata)
            metadata["chunk_index"] = counter
            metadata["chunk_id"] = f"{source}#chunk-{counter:03d}"
            metadata["section"] = section
            metadata["word_count"] = len(chunk.page_content.split())
            metadata["char_count"] = len(chunk.page_content)

            enriched_chunks.append(
                Document(
                    page_content=chunk.page_content.strip(),
                    metadata=metadata,
                )
            )

        logger.info(
            f"Split {len(documents)} source documents into {len(enriched_chunks)} chunks "
            f"(chunk_size={self.chunk_size}, overlap={self.chunk_overlap})"
        )
        return enriched_chunks
