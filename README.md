# Candidate Intelligence Platform (CIP)

> **Privacy-First, Local-First AI Candidate Intelligence & Résumé Retrieval Platform**

[![Python 3.14+](https://img.shields.io/badge/python-3.14%2B-blue.svg)](https://www.python.org/)
[![Database SQLite](https://img.shields.io/badge/database-SQLite_WAL-green.svg)](https://www.sqlite.org/)
[![Vector Store LanceDB](https://img.shields.io/badge/vector_store-LanceDB-orange.svg)](https://lancedb.github.io/lancedb/)
[![License MIT](https://img.shields.io/badge/license-MIT-purple.svg)](LICENSE)

Candidate Intelligence Platform (CIP) process, index, parse, search, manage candidate profiles, résumés, communication timelines locally. Combines CAS, SQLite WAL, LanceDB vector search, section chunker, entity resolution. Fast search, zero external API calls.

---

## 🌟 Key Features

- 📄 **Multi-Format Parsing**: Extract PDF (PyMuPDF, pdfplumber + OCR), Word (`.docx`), Outlook (`.msg`).
- 🔒 **Content-Addressable Storage (CAS)**: SHA-256 binary hash storage, exact deduplication.
- 🧩 **Section-Aware Chunker**: Segment docs preserving semantic context (work, education, skills).
- 🆔 **Two-Tier Entity Resolution**:
  - **Tier 1 (Deterministic)**: Exact match on email, phone, social.
  - **Tier 2 (Probabilistic)**: Jaro-Winkler name similarity matching.
- ⚡ **Hybrid Search**: **LanceDB** vector store + **SQLite WAL FTS5** full-text search.
- 🛡️ **100% Local & Private**: 100% offline, zero cloud dep.

---

## 🏗️ System Architecture

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
└───────────────────────────┘                               └───────────────────────────┘
```

---

## 🛠️ Technology Stack

| Component | Technology | Purpose |
| :--- | :--- | :--- |
| **Runtime** | Python `>=3.14` | Execution environment |
| **Package Manager** | `uv` / `uv_build` | Dependency management & project build |
| **Relational Database** | SQLite (WAL Mode) + SQLAlchemy 2.0 | Transactional storage & metadata |
| **Vector Database** | LanceDB `^0.36` | Embedded vector storage & ANN search |
| **PDF Extraction** | PyMuPDF + pdfplumber | Document parse & OCR text extract |
| **DOCX Extraction** | `python-docx` | Word doc parse |
| **Email Extraction** | `extract-msg` | Outlook `.msg` parse |
| **Validation** | Pydantic v2 & `pydantic-settings` | Schema validation |
| **Test Engine** | `pytest` | Unit & integration testing |

---

## 🚀 Getting Started

### Prerequisites

- **Python**: `>=3.14` installed.
- **uv**: Optional package manager.

### Installation

1. **Clone Repository**:
   ```bash
   git clone https://github.com/ArhamBafna/Candidate_Intelligence_Platform.git
   cd Candidate_Intelligence_Platform
   ```

2. **Set Up Environment**:
   ```bash
   # Using uv
   uv sync

   # Or standard venv
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   pip install -e .
   ```

3. **Verify Config**:
   Settings managed in `config/settings.py`.

---

## 📁 Repository Structure

```
Candidate_Intelligence_Platform/
├── AGENTS.md                  # Compressed guidelines for AI agents
├── README.md                  # Project overview & documentation
├── README.original.md         # Full human-readable backup README
├── pyproject.toml             # Project configuration & dependencies
├── config/                    # Global settings & SQLite setup (database.py, settings.py)
├── storage/                   # Storage layer (cas.py, db_models.py, vector_store.py)
├── ingestion/                 # Processing pipeline (parsers/, chunker.py, entity_resolution.py)
├── docs/                      # Arch specs & task roadmap (architecture_design_document.md, handoff.md, task.md)
└── tests/                     # Unit test suite
```

---

## 🧪 Testing

Run test suite via `pytest`:

```bash
pytest
pytest -v
pytest tests/test_entity_resolution.py
pytest tests/test_chunker.py
pytest tests/test_pdf_parser.py
```

---

## 🗺️ Status & Roadmap

Tracked in [`docs/task.md`](file:///c:/Users/Kamlesh/Desktop/arham-projects/Candidate_Intelligence_Platform/docs/task.md):

- [x] **Setup & Virtualenv** (`pyproject.toml`)
- [x] **Storage & Data Layer** (`SQLite WAL`, `CAS SHA-256`, `LanceDB`)
- [x] **Ingestion & Parsers** (`PDF`, `DOCX`, `MSG`, `Chunker`, `Entity Resolution`)
- [ ] **Extraction & Search** (NER, fastembed embeddings, hybrid rank, RRF)
- [ ] **CRM Timeline & Ops** (Stage state machine, backup sync)

---

## 📄 License

MIT License.
