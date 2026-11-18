# InsightIQ Production Deployment & Operations Guide

This guide details instructions for provisioning, configuring, and operating **InsightIQ** across local developer workstations and production containerized environments.

---

## 1. System Requirements & Prerequisites

### Hardware Recommendations
| Component | Minimum Specification | Recommended Specification |
| :--- | :--- | :--- |
| **CPU / Processor** | 4-Core x86_64 or ARM64 | 8-Core (Apple Silicon M1/M2/M3 or Intel/AMD Core i7/Ryzen 7) |
| **Memory (RAM)** | 8 GB RAM | 16 GB RAM or higher |
| **GPU Acceleration** | CPU Only (Quantized 3B LLM) | Apple Silicon Unified Memory or NVIDIA GPU (CUDA 12+) |
| **Disk Storage** | 15 GB free disk space | 30 GB SSD (for Docker images, PostgreSQL, and ChromaDB) |

### Software Prerequisites
- **Operating System:** macOS (Sonoma/Sequoia), Linux (Ubuntu 22.04+), or Windows 11 with WSL2.
- **Docker & Docker Compose:** Docker Engine 24.0+ and Docker Compose v2.20+.
- **Python:** Python 3.11 or 3.12 (if running natively).
- **Ollama:** Ollama v0.3.0+ (download from [ollama.com](https://ollama.com)).

---

## 2. Configuration & Environment Variables

InsightIQ manages configuration via a standard `.env` file. Copy the provided `.env.example`:

```bash
cp .env.example .env
```

### Key Configuration Parameters

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `POSTGRES_HOST` | `localhost` (or `postgres` in Docker) | Hostname of the PostgreSQL database |
| `POSTGRES_PORT` | `5433` (maps to internal 5432) | Host port exposed by Docker container |
| `POSTGRES_DB` | `insightiq` | Primary database name |
| `POSTGRES_USER` | `postgres` | Superuser for migrations and ingestion |
| `POSTGRES_PASSWORD` | `postgres` | Superuser password |
| `POSTGRES_READONLY_USER` | `insightiq_readonly` | Least-privilege user for AI agent queries |
| `POSTGRES_READONLY_PASSWORD` | `readonly_secret` | Read-only user password |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Endpoint of the Ollama service |
| `OLLAMA_MODEL` | `qwen2.5:3b` | Primary generative LLM model |
| `OLLAMA_EMBED_MODEL` | `nomic-embed-text` | 768-dimensional text embedding model |
| `CHROMA_PERSIST_DIRECTORY` | `./chroma_db` | Persistent directory for ChromaDB vectors |
| `SQL_QUERY_TIMEOUT_SECONDS` | `10` | Hard timeout for SQL query execution |
| `SQL_MAX_ROWS_RETURNED` | `500` | Safety limit for returned result set rows |

---

## 3. Deployment Methods

### Option A: Complete Multi-Container Stack (Docker Compose)
Runs PostgreSQL, Ollama, FastAPI Backend, and Streamlit Frontend in isolated containers:

```bash
# 1. Clone repository
git clone https://github.com/mivishvajeet/InsightHQ.git
cd InsightHQ

# 2. Build and launch all services
docker compose up -d --build

# 3. Pull required Ollama models inside container
docker exec -it insightiq-ollama ollama pull qwen2.5:3b
docker exec -it insightiq-ollama ollama pull nomic-embed-text

# 4. Ingest knowledge base documents into ChromaDB
docker exec -it insightiq-backend python -m backend.app.rag.indexer

# 5. Verify system health
docker exec -it insightiq-backend python scripts/verify_system.py
```

- **Streamlit Dashboard:** `http://localhost:8501`
- **FastAPI OpenAPI Docs:** `http://localhost:8000/docs`
- **PostgreSQL Port:** `localhost:5433`

---

### Option B: Local Developer Workstation Setup
Recommended for active development, debugging, and rapid iteration:

```bash
# 1. Start PostgreSQL container
docker compose up -d postgres

# 2. Start local Ollama daemon (in separate terminal)
ollama serve

# 3. Pull models locally
ollama pull qwen2.5:3b
ollama pull nomic-embed-text

# 4. Create and activate Python virtual environment
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 5. Populate ChromaDB knowledge base
python -m backend.app.rag.indexer

# 6. Verify end-to-end system health
python scripts/verify_system.py

# 7. Launch FastAPI backend
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload &

# 8. Launch Streamlit UI
streamlit run frontend/app.py
```

---

## 4. Verification & Testing Operations

### Comprehensive System Health Check
Run the automated verification script:
```bash
python scripts/verify_system.py
```
This tests database connection pools, table row baselines, Ollama latency, ChromaDB chunk count, SQL AST safety blocking, intent classification, and benchmark scorecard health.

### Full Automated Pytest Suite
Run the 104-test automated test suite:
```bash
pytest backend/tests/ -v
```

### Benchmark Evaluation Suite
Run the 35-question evaluation suite to verify accuracy and regression resistance:
```bash
python -m evaluation.run_evaluation
```

---

## 5. Troubleshooting & Operational Runbook

### Issue: PostgreSQL Port 5433 Connection Refused
- **Cause:** Docker Desktop was stopped or paused, or the container crashed.
- **Fix:** Run `docker ps` to verify the container `insightiq-postgres` is healthy. Restart with `docker compose up -d postgres`.

### Issue: Ollama Timeout or Slow Generation
- **Cause:** CPU contention or large context window on low-memory machines.
- **Fix:** Keep model resident in memory:
  ```bash
  export OLLAMA_KEEP_ALIVE=24h
  ```
  Ensure Ollama utilizes GPU acceleration (Metal on macOS, CUDA on Linux).

### Issue: Vector Store Out-of-Sync or Corrupt
- **Cause:** Markdown files in `knowledge_base/` were modified or chunk format updated.
- **Fix:** Rebuild the vector database from source markdown files:
  ```bash
  python -m backend.app.rag.indexer --rebuild
  ```

