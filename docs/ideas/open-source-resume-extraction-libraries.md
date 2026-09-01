# Next-Gen Open-Source Resume Extraction & Vector Database Indexing

**Status:** `PROPOSED`  
**Category:** Ingestion / Extraction / Vector Store / AI Pipeline  

---

## 1. Overview & Motivation

Currently, CIP's extraction pipeline relies on traditional PyMuPDF/python-docx text dumps combined with deterministic regex NER (`deterministic_ner.py`) and fallback LLM extraction (`local_llm_fallback.py`).

While effective for standard single-column resumes, resumes in the wild frequently suffer from **layout chaos**:
- Multi-column formats where horizontal text dumps concatenate unrelated blocks (e.g. skills in a sidebar merging into job descriptions).
- Nested tables and non-standard font hierarchies.
- Inconsistent entity extraction across varied ATS templates.

To achieve enterprise-grade accuracy while preserving CIP's **privacy-first and local-first** core, this document outlines the top open-source parsing libraries, structured extraction frameworks, and all-in-one vector database ingestion toolkits.

---

## 2. Open-Source Landscape & Library Evaluation

### A. Dedicated Resume Parsers

1. **[pyresume (LeverParser)](https://github.com/wespiper/pyresume)**
   - **Approach:** Local NLP + Optional Local LLM.
   - **Strengths:** Emulates modern Lever ATS extraction; developer-friendly, privacy-centric (no external API requirement), extracts contact info, work history, skills, and education.
   - **Fit for CIP:** High potential as an off-the-shelf local parser or reference architecture.

2. **[orasik/resume-parser](https://github.com/orasik/resume-parser)**
   - **Approach:** PyMuPDF + Schema-driven LLM JSON extraction.
   - **Strengths:** High accuracy across varying layouts; formats directly to structured JSON matching ATS schemas.
   - **Fit for CIP:** Proves the efficacy of schema-constrained LLM parsing.

3. **[pyresparser](https://github.com/OmkarPathak/pyresparser)**
   - **Approach:** Classic spaCy + Regex baseline.
   - **Strengths:** Fast, deterministic.
   - **Limitations:** Brittle with multi-column layouts, legacy dependencies (`nltk`, `textract`).

---

### B. Next-Gen Document & Layout Analyzers (Foundation Layer)

1. **[IBM Docling (`docling`)](https://github.com/DS4SD/docling)**
   - **Key Advantage:** State-of-the-art open-source, local document understanding (MIT licensed).
   - **Features:** Reads complex multi-column PDFs/DOCX, performs layout detection, and outputs structured Markdown and bounding-box JSON while strictly preserving human reading order.
   - **Impact on CIP:** Eliminates cross-column text scrambling before text reaches NER or LLMs.

2. **[Marker (`marker-pdf`)](https://github.com/VikParuchuri/marker)**
   - Deep learning pipeline converting PDF documents to clean Markdown (tables, bullet points, headers).

---

### C. Constrained Structured Extraction Frameworks

1. **[Instructor (`instructor`)](https://github.com/jxnl/instructor)**
   - Wraps local LLM runtimes (Ollama, llama-cpp-python, vLLM) with strict Pydantic v2 validation.
   - Guarantees 100% compliant nested JSON schemas (Candidate Profile, Work History timeline, Skills taxonomy, Education, Claims) with automatic validation retries.

2. **[Outlines (`outlines`)](https://github.com/dottxt-ai/outlines)**
   - Guided grammar/regex logit masking for local models, ensuring syntactically valid JSON output with zero prompt hallucination overhead.

---

### D. All-in-One Vector DB Ingestion Frameworks (Automatic Extract + Vector Store)

Libraries and frameworks specifically designed to handle parsing, chunking, embedding, and automatic indexing directly into vector databases:

1. **[Unstructured.io (`unstructured`)](https://github.com/Unstructured-IO/unstructured)** *(Industry Standard ETL)*
   - **How it works:** Complete ETL framework for vector databases. Partitions raw files (PDFs, DOCX, emails) using layout-aware intelligence, chunks text into semantic blocks, and provides built-in connectors to vector stores.
   - **Vector DB Connectors:** Native support for LanceDB, Chroma, Qdrant, Milvus, and Pinecone.
   - **Pipeline Pattern:**
     ```python
     from unstructured.partition.pdf import partition_pdf
     from sentence_transformers import SentenceTransformer
     import lancedb

     elements = partition_pdf("resume.pdf")
     resume_text = "\n".join([str(el) for el in elements])
     ```
   - **Fit for CIP:** High fit for clean layout chunking with direct vector store ingestion.

2. **[LlamaIndex (`llama-index`)](https://github.com/run-llama/llama_index)** *(Best for Structured + Vector Workflows)*
   - **How it works:** Provides document readers (`SimpleDirectoryReader`) paired with ingestion pipelines and vector store connectors.
   - **LanceDB Integration:**
     ```python
     from llama_index.core import SimpleDirectoryReader, VectorStoreIndex
     from llama_index.vector_stores.lancedb import LanceDBVectorStore

     vector_store = LanceDBVectorStore(uri="./storage/lancedb", table_name="resumes")
     documents = SimpleDirectoryReader(input_files=["resume.pdf"]).load_data()
     # Automatically parses, embeds via local FastEmbed, and indexes to LanceDB
     index = VectorStoreIndex.from_documents(documents, vector_store=vector_store)
     ```
   - **Fit for CIP:** Seamless native fit with CIP's existing LanceDB vector store and fastembed embeddings.

3. **[Embedchain (`embedchain` / Mem0)](https://github.com/mem0ai/mem0)** *(Single-Command Ingestion)*
   - **How it works:** Minimal abstraction layer for instant parse + embed + store in 2 lines:
     ```python
     from embedchain import App
     app = App()  # Local ChromaDB/LanceDB + local embeddings
     app.add("candidate_resume.pdf", data_type="pdf_file")
     results = app.query("Find candidates with 5+ years of FastAPI and LanceDB experience")
     ```
   - **Fit for CIP:** Good for quick prototypes, though offers less granular schema control than CIP's explicit candidate claims ledger.

4. **[Haystack by deepset (`haystack-ai`)](https://github.com/deepset-ai/haystack)** *(Production Pipeline Architecture)*
   - **How it works:** Modular directed graphs: `PDFToText -> Cleaner -> DocumentSplitter -> Embedder -> DocumentWriter (VectorDB)`.
   - **Fit for CIP:** Scalable orchestration for complex multi-stage agentic retrieval.

---

### E. Framework Comparison Summary

| Library | Primary Strength | Automatic Vector DB Support | Fit for CIP |
| :--- | :--- | :--- | :--- |
| **`docling`** | Best layout & multi-column table parsing | Export to Markdown/JSON | **Very High** (Document pre-processing) |
| **`instructor`** | Pydantic v2 validation with local LLMs (Ollama) | Via Pydantic models | **Very High** (Structured claims extraction) |
| **`unstructured`** | Layout ETL + Vector DB connectors | Direct connectors (LanceDB, Qdrant) | **High** (ETL pipeline) |
| **`llama-index`** | Native LanceDB vector indexer + Readers | Native `LanceDBVectorStore` | **High** (Drop-in vector store pipeline) |
| **`pyresume`** | Lever-style ATS local extraction | Exports structured JSON | **High** (Domain-specific extraction) |
| **`embedchain`** | Zero-config instant prototype | Native (Chroma, Qdrant) | **Medium** (Less granular claim tracking) |

---

## 3. Proposed CIP Target Architecture

```
Raw File (PDF / DOCX / EML)
       │
       ▼
[SHA-256 CAS Deduplication] (Existing)
       │
       ▼
[Layout-Aware Parser (e.g. Docling / Unstructured / PyMuPDF Columns)]
   ──► Converts to Clean Structured Markdown (Preserves reading order & tables)
       │
       ▼
[Hybrid Extraction Engine]
   ├── 1. Deterministic Extraction (Fast regex for emails, phones, links, known skills)
   └── 2. Local Structured LLM Extraction (Instructor + Pydantic v2 + Ollama)
          ──► Extracts work experiences, job titles, dates, certifications, visas
       │
       ▼
[Pydantic v2 Candidate Claims & Profile Validation]
       │
       ▼
[SQLite WAL + LanceDB Embeddings + Timeline Ledger] (Existing)
```

---

## 4. Implementation Steps & Roadmap

1. **Benchmark & Evaluation**:
   - Create a benchmark test suite using diverse resume formats (single-column, two-column sidebar, tabular).
   - Benchmark `Docling` / `Unstructured` vs `PyMuPDF` layout extraction quality and speed.
2. **Pydantic Extraction Schema**:
   - Define a comprehensive `ExtractedResumeSchema` in `candidate_intelligence_platform` to capture:
     - Contact details (name, email, phone, location, links)
     - Work experience (company, title, start/end dates, bullets/responsibilities)
     - Education (degree, institution, graduation year)
     - Skills, tools, and certifications
     - Work authorization / visa signals
3. **Local LLM Structured Output Integration**:
   - Integrate `instructor` with CIP's existing Ollama client configuration.
4. **Vector Pipeline Integration**:
   - Explore integrating layout chunkers directly into CIP's LanceDB table loader.
5. **Testing & Performance Validation**:
   - Ensure all model operations remain fast and mockable in unit tests (< 2s per test file) per `AGENTS.md`.

---

## TO CHECK IN FUTURE:
- https://github.com/OmkarPathak/ResumeParser
