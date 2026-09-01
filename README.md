# Candidate Intelligence Platform (CIP)

> Local candidate intelligence and résumé retrieval platform.

[![Python 3.14+](https://img.shields.io/badge/python-3.14%2B-blue.svg)](https://www.python.org/)
[![Database SQLite](https://img.shields.io/badge/database-SQLite_WAL-green.svg)](https://www.sqlite.org/)
[![Vector Store LanceDB](https://img.shields.io/badge/vector_store-LanceDB-orange.svg)](https://lancedb.github.io/lancedb/)
[![License MIT](https://img.shields.io/badge/license-MIT-purple.svg)](LICENSE)

Candidate Intelligence Platform (CIP) parses, indexes, searches, and manages candidate profiles, résumés, and communication timelines locally without external API dependencies.

---

## Key features

- Document parsing: extracts text and metadata from PDF (PyMuPDF, pdfplumber with OCR), Word (`.docx`), and Outlook (`.msg`) files.
- Content-addressable storage: deduplicates files using SHA-256 hashes.
- Section-aware chunking: segments documents while preserving semantic context across work, education, and skills.
- Two-tier entity resolution: combines exact matches on email, phone, and social profiles with Jaro-Winkler name similarity.
- Hybrid search: pairs LanceDB vector search with SQLite FTS5 full-text indexing.
- Web dashboard and API: provides a FastAPI backend alongside a recruiter dashboard built with Vite, React, and Tailwind CSS.
- Local execution: runs completely offline with no required cloud services.

---

## System architecture

```
                               ┌─────────────────────────┐
                               │ Raw Files (PDF/DOCX/MSG)│
                               └────────────┬────────────┘
                                            │
                                            ▼
                               ┌─────────────────────────┐
                               │ Content-Addressable Store│ (SHA-256 Deduplication)
                               └────────────┬────────────┘
                                            │
                                            ▼
                               ┌─────────────────────────┐
                               │    Document Parsers     │ (PDF, DOCX, Email)
                               └────────────┬────────────┘
                                            │
                                            ▼
                               ┌─────────────────────────┐
                               │ Section-Aware Chunker   │ (Semantic Chunking)
                               └────────────┬────────────┘
                                            │
                                            ▼
                               ┌─────────────────────────┐
                               │ Entity Resolution Engine│ (Tier 1 & Tier 2 Matching)
                               └──────┬───────────┬──────┘
                                      │           │
              ┌───────────────────────┘           └───────────────────────┐
              ▼                                                           ▼
┌───────────────────────────┐                               ┌───────────────────────────┐
│   SQLite Database (WAL)   │                               │      LanceDB Vector       │
│ (Profiles, Records, FTS5) │                               │      Embedded Table       │
└─────────────┬─────────────┘                               └─────────────┬─────────────┘
              │                                                           │
              └───────────────────────────┬───────────────────────────────┘
                                          │
                                          ▼
                             ┌─────────────────────────┐
                             │   FastAPI REST Backend  │ (API & Hybrid Search Ranks)
                             └────────────┬────────────┘
                                          │
                                          ▼
                             ┌─────────────────────────┐
                             │  React + Tailwind UI    │ (Recruiter Dashboard)
                             └─────────────────────────┘
```

---

## Technology stack

| Component | Technology | Purpose |
| :--- | :--- | :--- |
| **Runtime** | Python `>=3.14` | Execution environment |
| **Package Manager** | `uv` / `uv_build` | Dependency management and build |
| **Relational Database** | SQLite (WAL Mode) + SQLAlchemy 2.0 | Transactional storage and metadata |
| **Vector Database** | LanceDB `^0.36` | Embedded vector storage and ANN search |
| **API Framework** | FastAPI `^0.141` | REST services and endpoints |
| **Frontend Framework** | Vite + React + Tailwind CSS | Recruiter web dashboard |
| **PDF Extraction** | PyMuPDF + pdfplumber | Document parsing and OCR text extraction |
| **DOCX Extraction** | `python-docx` | Word document parsing |
| **Email Extraction** | `extract-msg` | Outlook `.msg` parsing |
| **Validation** | Pydantic v2 & `pydantic-settings` | Schema validation |
| **Test Engine** | `pytest` | Unit and integration testing |

---

## Getting started

### Prerequisites

- Python `>=3.14`, Node.js `>=18`, Git
- `uv`: `powershell -c "irm https://astral.sh/uv/install.ps1 | iex"` (ensure `~/.local/bin` in PATH)
- Ollama (offline AI extraction): `winget install Ollama.Ollama` or [ollama.com](https://ollama.com/download/windows)

### Quickstart

1. **Clone repository and install dependencies**:
   ```bash
   git clone https://github.com/ArhamBafna/Candidate_Intelligence_Platform.git
   cd Candidate_Intelligence_Platform
   uv sync
   ```

2. **Download extraction model**:
   ```bash
   ollama pull llama3.2
   ```

3. **Start backend API**:
   ```bash
   uv run uvicorn api.main:app --reload
   ```

4. **Start recruiter dashboard**:
   ```bash
   cd ui && npm install && npm run dev
   ```

### Configuration (optional)

| Variable | Default | Description |
| :--- | :--- | :--- |
| `CIP_LLM_MODEL` | `llama3.2` | Local LLM model |
| `OLLAMA_HOST` | `http://localhost:11434` | Ollama service endpoint |

---

## Repository structure

```
Candidate_Intelligence_Platform/
├── AGENTS.md                  # Guidelines for AI agents
├── README.md                  # Project overview and documentation
├── pyproject.toml             # Project configuration and dependencies
├── config/                    # Global settings and database configuration
├── storage/                   # Storage layer (CAS, database models, LanceDB)
├── ingestion/                 # Pipeline (parsers, chunker, entity resolution)
├── api/                       # FastAPI routes, dependencies, schemas
├── ui/                        # Recruiter UI (Vite + React + Tailwind CSS)
├── docs/                      # Architecture specifications and roadmaps
└── tests/                     # Test suite
```

---

## Testing

```bash
# Run test suite
uv run pytest

# Verify local LLM fallback
uv run pytest tests/test_local_llm_fallback.py
```

### Search accuracy evaluation (golden set)

The golden-set harness measures Recall@10 and MRR for hybrid search over `tests/fixtures/golden_search_set.json` using local FastEmbed and cross-encoder models. These tests are skipped during default test runs.

```bash
# Run evaluation against the baseline
uv run pytest tests/test_golden_eval.py -m evaluation --run-eval -q -s

# Regenerate baseline
uv run pytest tests/test_golden_eval.py -m evaluation --run-eval --update-baseline -q
```

---

## Status and roadmap

Tracked in [`docs/task.md`](docs/task.md):

- [x] **Setup & Virtualenv** (`pyproject.toml`)
- [x] **Storage & Data Layer** (`SQLite WAL`, `CAS SHA-256`, `LanceDB`)
- [x] **Ingestion & Parsers** (`PDF`, `DOCX`, `MSG`, `Chunker`, `Entity Resolution`)
- [x] **Extraction & Search** (NER, fastembed embeddings, hybrid rank, RRF)
- [x] **CRM Timeline & Ops** (Stage state machine, backup sync)
- [x] **API & Recruiter Interface** (FastAPI, React + Tailwind UI)

---

## License

MIT License.
