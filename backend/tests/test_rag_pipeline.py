"""
Comprehensive Test Suite for InsightIQ RAG Subsystem.

Tests:
1. Knowledge base file integrity and document loading
2. Markdown-aware text splitting and chunk metadata
3. ChromaDB vector storage and semantic retrieval relevance
4. Context-grounded response generation
5. Out-of-scope query limitation reporting
6. Citation extraction and score normalization
"""

import pytest
from pathlib import Path

from backend.app.rag.config import KNOWLEDGE_BASE_DIR
from backend.app.rag.document_loader import KnowledgeBaseLoader, DOCUMENT_CATEGORIES, REQUIRED_DOCUMENTS
from backend.app.rag.text_splitter import MarkdownTextSplitter
from backend.app.rag.retriever import SemanticRetriever, Citation, RetrievalResult
from backend.app.rag.pipeline import rag_pipeline
from backend.app.services.llm_client import OllamaClient


def test_required_knowledge_base_files_exist():
    """Verify that all 7 mandatory markdown documentation files exist."""
    loader = KnowledgeBaseLoader()
    status = loader.validate_knowledge_base()
    for filename in REQUIRED_DOCUMENTS:
        assert status.get(filename) is True, f"Missing required documentation: {filename}"


def test_document_loader_metadata_enrichment():
    """Verify that documents are parsed with correct metadata."""
    loader = KnowledgeBaseLoader()
    docs = loader.load_documents()
    assert len(docs) == len(REQUIRED_DOCUMENTS)

    sources = [d.metadata["source"] for d in docs]
    for filename in REQUIRED_DOCUMENTS:
        assert filename in sources

    for doc in docs:
        assert "title" in doc.metadata
        assert "category" in doc.metadata
        assert "char_count" in doc.metadata
        assert doc.metadata["char_count"] > 200
        assert doc.metadata["category"] == DOCUMENT_CATEGORIES[doc.metadata["source"]]


def test_markdown_text_splitter():
    """Verify that text splitting produces cohesive chunks with section headers."""
    loader = KnowledgeBaseLoader()
    docs = loader.load_documents()
    splitter = MarkdownTextSplitter(chunk_size=500, chunk_overlap=100)
    chunks = splitter.split_documents(docs)

    assert len(chunks) >= 20
    for chunk in chunks:
        assert "chunk_id" in chunk.metadata
        assert "section" in chunk.metadata
        assert "word_count" in chunk.metadata
        assert chunk.metadata["word_count"] > 0
        assert len(chunk.page_content) <= 700


def test_semantic_retrieval_relevance():
    """Test that standard domain business queries retrieve relevant source documents."""
    retriever = SemanticRetriever()

    test_cases = [
        ("What is the definition of average order value?", "metric_definitions.md"),
        ("How is customer retention calculated?", "customer_analytics.md"),
        ("Explain the database schema and table relationships", "database_schema.md"),
        ("What does a delivered order mean in this project?", "sales_business_rules.md"),
        ("Are delivery delays associated with lower review scores?", "review_analysis.md"),
    ]

    for query, expected_source in test_cases:
        result = retriever.retrieve(query=query, top_k=3)
        assert result.total_found > 0
        retrieved_sources = [c.source for c in result.citations]
        assert expected_source in retrieved_sources, (
            f"Query '{query}' expected '{expected_source}' in top results, got {retrieved_sources}"
        )


def test_citation_data_structure():
    """Test that citations contain valid metadata and scores."""
    retriever = SemanticRetriever()
    result = retriever.retrieve("customer repeat rate", top_k=2)

    assert len(result.citations) > 0
    top_citation = result.citations[0]
    assert isinstance(top_citation, Citation)
    assert top_citation.source.endswith(".md")
    assert 0.0 <= top_citation.relevance_score <= 1.0
    assert len(top_citation.snippet) > 10


def test_out_of_scope_query_limitation():
    """Verify that out-of-scope questions without relevant context disclose limitations."""
    out_of_scope_query = "What is the quarterly dividend payout for Apple AAPL stock?"
    # Chroma will retrieve low-similarity docs, but LLM or generator must report limitation
    answer = rag_pipeline.answer_question(out_of_scope_query, top_k=2)
    assert answer.has_limitation is True or "not contain" in answer.answer.lower() or "not mentioned" in answer.answer.lower()
