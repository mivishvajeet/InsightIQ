"""
Document Loader for InsightIQ Knowledge Base.

Loads domain markdown documents from the knowledge_base directory, extracts rich metadata,
and prepares structured LangChain Document objects for downstream chunking and vector indexing.
"""

import os
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from langchain_core.documents import Document

from backend.app.rag.config import KNOWLEDGE_BASE_DIR

logger = logging.getLogger(__name__)

# Categorization mapping for knowledge base documents
DOCUMENT_CATEGORIES = {
    "business_overview.md": "overview",
    "database_schema.md": "schema",
    "metric_definitions.md": "metrics",
    "sales_business_rules.md": "business_rules",
    "customer_analytics.md": "customer_analytics",
    "delivery_policies.md": "logistics",
    "review_analysis.md": "customer_satisfaction",
}

REQUIRED_DOCUMENTS = list(DOCUMENT_CATEGORIES.keys())


class KnowledgeBaseLoader:
    """Loads and enriches business documentation from the markdown knowledge base."""

    def __init__(self, directory: Optional[Path] = None):
        self.directory = Path(directory) if directory else KNOWLEDGE_BASE_DIR

    def validate_knowledge_base(self) -> Dict[str, bool]:
        """Checks if all required markdown documents exist in the knowledge base directory."""
        status = {}
        for filename in REQUIRED_DOCUMENTS:
            filepath = self.directory / filename
            status[filename] = filepath.exists()
        return status

    def load_documents(self) -> List[Document]:
        """
        Loads all markdown documents from the directory and attaches structured metadata.
        """
        if not self.directory.exists():
            raise FileNotFoundError(f"Knowledge base directory not found at: {self.directory}")

        documents: List[Document] = []
        md_files = sorted(list(self.directory.glob("*.md")))

        if not md_files:
            logger.warning(f"No markdown files found in {self.directory}")
            return documents

        for filepath in md_files:
            filename = filepath.name
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()

                # Extract title from first H1 if present
                lines = content.splitlines()
                title = filename.replace(".md", "").replace("_", " ").title()
                for line in lines:
                    if line.startswith("# "):
                        title = line.replace("# ", "").strip()
                        break

                category = DOCUMENT_CATEGORIES.get(filename, "general")

                doc = Document(
                    page_content=content,
                    metadata={
                        "source": filename,
                        "title": title,
                        "category": category,
                        "file_path": str(filepath.resolve()),
                        "char_count": len(content),
                        "line_count": len(lines),
                    },
                )
                documents.append(doc)
                logger.info(f"Loaded document '{filename}' ({len(content)} chars, {len(lines)} lines)")

            except Exception as e:
                logger.error(f"Error loading document {filepath}: {e}")
                raise

        return documents
