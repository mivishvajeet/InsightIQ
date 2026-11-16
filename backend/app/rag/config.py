"""
RAG and Vector Database Configuration for InsightIQ.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
KNOWLEDGE_BASE_DIR = BASE_DIR / "knowledge_base"
DEFAULT_CHROMA_DIR = BASE_DIR / "data" / "processed" / "chroma_db"

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")
LLM_MODEL = os.getenv("LLM_MODEL", "qwen2.5:3b")

CHROMA_PERSIST_DIRECTORY = Path(os.getenv("CHROMA_PERSIST_DIRECTORY", str(DEFAULT_CHROMA_DIR)))
CHROMA_COLLECTION_NAME = "insightiq_knowledge_base"

# Chunking specifications
CHUNK_SIZE = 600
CHUNK_OVERLAP = 120

# Retrieval specifications
DEFAULT_TOP_K = 4
SIMILARITY_SCORE_THRESHOLD = 0.35  # Maximum distance or minimum similarity
