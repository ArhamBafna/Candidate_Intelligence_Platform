# Candidate Intelligence Platform (CIP)

> **A Privacy-First, Local-First AI Candidate Intelligence & Résumé Retrieval Platform**

[![Python 3.14+](https://img.shields.io/badge/python-3.14%2B-blue.svg)](https://www.python.org/)
[![Database SQLite](https://img.shields.io/badge/database-SQLite_WAL-green.svg)](https://www.sqlite.org/)
[![Vector Store LanceDB](https://img.shields.io/badge/vector_store-LanceDB-orange.svg)](https://lancedb.github.io/lancedb/)
[![License MIT](https://img.shields.io/badge/license-MIT-purple.svg)](LICENSE)

The **Candidate Intelligence Platform (CIP)** is an enterprise-grade, privacy-centric platform engineered to process, index, parse, search, and manage candidate profiles, résumés, and communication timeline events completely locally. By combining Content-Addressable Storage (CAS), relational database indexing, vector search, section-aware document chunking, and deterministic/probabilistic entity resolution, CIP delivers instant search capabilities without external data transmission.

---

## 🌟 Key Features

- 📄 **Multi-Format Document Parsing**: High-fidelity extraction from PDF (PyMuPDF, pdfplumber with OCR fallback), Word (`.docx`), and Outlook/email messages (`.msg`).
- 🔒 **Content-Addressable Storage (CAS)**: SHA-256 binary hash storage guaranteeing exact file deduplication and audit integrity.
- 🧩 **Section-Aware Hierarchical Chunker**: Intelligent document segmentation preserving semantic context across work experience, education, skills, and certifications.
- 🆔 **Two-Tier Entity Resolution**:
  - **Tier 1 (Deterministic)**: Exact matching on normalized email, phone, and social handles.
  - **Tier 2 (Probabilistic)**: Jaro-Winkler name similarity matching with configurable threshold scoring.
- ⚡ **Hybrid Search & Vector Indexing**: Integrated **LanceDB** vector store alongside **SQLite WAL-mode FTS5** full-text search for fast hybrid candidate retrieval.
- 🛡️ **100% Local & Private**: Operates fully offline without external API keys or cloud data exposure.

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
| **Runtime** | Python `>=3.14` | Core execution environment |
| **Package Manager** | `uv` / `uv_build` | Dependency management & project build |
| **Relational Database** | SQLite (WAL Mode) + SQLAlchemy 2.0 | Transactional storage & metadata |
| **Vector Database** | LanceDB `^0.36` | High-dimensional embedding storage & ANN search |
| **PDF Extraction** | PyMuPDF + pdfplumber | Document parsing & OCR text extraction |
| **DOCX Extraction** | `python-docx` | Structured Word document parsing |
| **Email Extraction** | `extract-msg` | Outlook `.msg` parser & metadata reader |
| **Validation** | Pydantic v2 & `pydantic-settings` | Structured schema verification |
| **Test Engine** | `pytest` | Automated unit & integration testing |

---

## 🚀 Getting Started

### Prerequisites

- **Python**: Version 3.14 or higher installed.
- **uv** (Optional but recommended): High-performance Python package installer.

### Installation

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/ArhamBafna/Candidate_Intelligence_Platform.git
   cd Candidate_Intelligence_Platform
   ```

2. **Set Up Environment**:
   ```bash
   # Using uv
   uv sync

   # Or using standard venv
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -e .
   ```

3. **Verify Configuration**:
   Environment settings are managed dynamically in `config/settings.py`.

---

## 📁 Repository Structure

```
Candidate_Intelligence_Platform/
├── AGENTS.md                  # Comprehensive guidelines for AI agents & contributors
├── README.md                  # Project overview & documentation
├── pyproject.toml             # Project build configuration & dependencies
├── config/                    # Global app configuration & SQLite pool setup
│   ├── database.py            # SQLite WAL mode engine configuration
│   └── settings.py            # Pydantic base settings (Paths, CAS root)
├── storage/                   # Core storage & database layers
│   ├── cas.py                 # Content-Addressable Storage (SHA-256)
│   ├── db_models.py           # SQLAlchemy ORM models & table definitions
│   └── vector_store.py        # LanceDB vector manager
├── ingestion/                 # Processing & parsing pipeline
│   ├── parsers/               # Multi-format document parsers (PDF, DOCX, Email)
│   ├── chunker.py             # Section-aware text chunking engine
│   └── entity_resolution.py   # Tier 1 exact & Tier 2 Jaro-Winkler resolution
├── docs/                      # Architectural specs & feature tracking
│   ├── architecture_design_document.md
│   ├── handoff.md
│   └── task.md                # Interactive project task roadmap
└── tests/                     # Automated unit test suite
```

---

## 🧪 Testing

Run the complete test suite using `pytest`:

```bash
# Run all unit tests
pytest

# Run tests with detailed log output
pytest -v

# Run specific test modules
pytest tests/test_entity_resolution.py
pytest tests/test_chunker.py
pytest tests/test_pdf_parser.py
```

---

## 🗺️ Project Status & Roadmap

Progress is tracked in [`docs/task.md`](file:///c:/Users/Kamlesh/Desktop/arham-projects/Candidate_Intelligence_Platform/docs/task.md):

- [x] **Project Bootstrapping & Setup** (`pyproject.toml`, virtualenv setup)
- [x] **Core Storage & Data Layer** (`SQLite WAL`, `CAS SHA-256`, `LanceDB`)
- [x] **Ingestion & Parsers** (`PDF`, `DOCX`, `MSG`, `Chunker`, `Entity Resolution`)
- [ ] **Fact Extraction & Search Engine** (NER, fastembed embeddings, hybrid filter-rank, RRF)
- [ ] **CRM Timeline Ledger & Operational Core** (Stage state machine, automated backup sync)

---

## 📄 License

This project is open-source and available under the [MIT License](LICENSE).
