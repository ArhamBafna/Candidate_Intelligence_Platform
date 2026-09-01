# Next-Gen Open-Source Resume Extraction & Layout Parsing

**Status:** `PROPOSED`  
**Category:** Ingestion / Extraction / NLP / AI Pipeline  

---

## 1. Overview & Motivation

Currently, CIP's extraction pipeline relies on traditional PyMuPDF/python-docx text dumps combined with deterministic regex NER (`deterministic_ner.py`) and fallback LLM extraction (`local_llm_fallback.py`).

While effective for standard single-column resumes, resumes in the wild frequently suffer from **layout chaos**:
- Multi-column formats where horizontal text dumps concatenate unrelated blocks (e.g. skills in a sidebar merging into job descriptions).
- Nested tables and non-standard font hierarchies.
- Inconsistent entity extraction across varied ATS templates.

To achieve enterprise-grade accuracy while preserving CIP's **privacy-first and local-first** core, we propose evaluating and integrating modern open-source parsing and structured extraction frameworks.

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

### B. Next-Gen Document & Layout Analyzers (Foundation Layer)

1. **[IBM Docling (`docling`)](https://github.com/DS4SD/docling)**
   - **Key Advantage:** State-of-the-art open-source, local document understanding (MIT licensed).
   - **Features:** Reads complex multi-column PDFs/DOCX, performs layout detection, and outputs structured Markdown and bounding-box JSON while strictly preserving human reading order.
   - **Impact on CIP:** Eliminates cross-column text scrambling before text reaches NER or LLMs.

2. **[Marker (`marker-pdf`)](https://github.com/VikParuchuri/marker)**
   - Deep learning pipeline converting PDF documents to clean Markdown (tables, bullet points, headers).

### C. Constrained Structured Extraction Frameworks

1. **[Instructor (`instructor`)](https://github.com/jxnl/instructor)**
   - Wraps local LLM runtimes (Ollama, llama-cpp-python, vLLM) with strict Pydantic v2 validation.
   - Guarantees 100% compliant nested JSON schemas (Candidate Profile, Work History timeline, Skills taxonomy, Education, Claims) with automatic validation retries.

2. **[Outlines (`outlines`)](https://github.com/dottxt-ai/outlines)**
   - Guided grammar/regex logit masking for local models, ensuring syntactically valid JSON output with zero prompt hallucination overhead.

---

## 3. Proposed CIP Target Architecture

```
Raw File (PDF / DOCX / EML)
       │
       ▼
[SHA-256 CAS Deduplication] (Existing)
       │
       ▼
[Layout-Aware Parser (e.g. Docling / PyMuPDF Columns)]
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
   - Benchmark `Docling` vs `PyMuPDF` layout extraction quality and speed.
2. **Pydantic Extraction Schema**:
   - Define a comprehensive `ExtractedResumeSchema` in `candidate_intelligence_platform` to capture:
     - Contact details (name, email, phone, location, links)
     - Work experience (company, title, start/end dates, bullets/responsibilities)
     - Education (degree, institution, graduation year)
     - Skills, tools, and certifications
     - Work authorization / visa signals
3. **Local LLM Structured Output Integration**:
   - Integrate `instructor` with CIP's existing Ollama client configuration.
4. **Testing & Performance Validation**:
   - Ensure all model operations remain fast and mockable in unit tests (< 2s per test file) per `AGENTS.md`.
