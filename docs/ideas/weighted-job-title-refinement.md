# Weighted Job Title Extraction & Refinement

**Status:** `OPEN / READY FOR IMPLEMENTATION`  
**Priority:** High  
**Prerequisites:** Issue #12 (Unified Intake Pipeline)  

---

## 1. Problem Statement

Deterministic job title extraction currently relies on keyword matching without syntactic awareness or section boundaries. As a result:
- Verbs and conversational phrases are misclassified as job titles:
  - Sentence: `"Able lead development team..."` $\rightarrow$ extracted: `"Able lead"`.
  - Sentence: `"Helped manage cloud migration..."` $\rightarrow$ extracted: `"Helped manage"`.
- Education degrees containing engineering terms are misclassified:
  - Education line: `"Bachelors in Computer Science and Engineer"` $\rightarrow$ extracted: `"Bachelors in Computer Science and Engineer"`.
- Extraneous adjectives clutter professional titles:
  - Summary: `"Proven Backend Engineer with 7 years experience..."` $\rightarrow$ extracted: `"Proven Backend Engineer"`.

---

## 2. Target Files & Architecture

| File | Changes Required |
|---|---|
| `src/candidate_intelligence_platform/extraction/deterministic_ner.py` | Implement `extract_job_title_weighted()` with section weighting, prefix stripping, role grammar matching, and verb exclusion. |
| `src/candidate_intelligence_platform/extraction/hybrid_extractor.py` | Integrate weighted title score into Tier-1 confidence assessment; trigger LLM fallback if title score $< 0.50$. |
| `tests/test_deterministic_ner.py` | Add unit tests covering noisy headers, degrees, verb phrases, and adjective prefixes. |

---

## 3. Detailed Technical Specification

### 3.1 Section-Weighted Confidence Scoring

When analyzing resume text lines, assign a location multiplier ($W_{\text{section}}$) based on where the candidate title phrase appears:

| Section / Region | Line Heuristic | Weight ($W_{\text{section}}$) | Rationale |
|---|---|---|---|
| **Header / Sub-header** | Lines 1–10 (directly below candidate name) | **1.00** | Canonical location for target/current title |
| **Work History Section Header** | Preceded by `"Experience"`, `"Work History"` | **0.85** | Current or most recent job title |
| **Summary / Objective** | Preceded by `"Summary"`, `"About Me"`, `"Profile"` | **0.65** | Self-declared professional identity |
| **Projects Section** | Preceded by `"Projects"`, `"Key Projects"` | **0.35** | Role on a specific project, often temporary |
| **Education Section** | Preceded by `"Education"`, `"Academics"` | **0.10** | High risk of degree false positives |

### 3.2 Syntactic Prefix Stripper

Strip promotional, conversational, or objective prefixes before scoring the title:

```python
TITLE_PREFIX_REGEX = re.compile(
    r"^(?:"
    r"proven|experienced|dynamic|dedicated|passionate|seasoned|"
    r"able\s+to|able|skilled|senior-level|junior-level|aspiring|"
    r"seeking\s+(?:a\s+)?(?:role|position)\s+as(?:\s+a)?|"
    r"looking\s+for\s+(?:a\s+)?(?:role|position)\s+as(?:\s+a)?"
    r")\s+",
    re.IGNORECASE,
)

def strip_title_noise(raw_title: str) -> str:
    cleaned = TITLE_PREFIX_REGEX.sub("", raw_title.strip())
    # Strip trailing punctuation, experience tags, and location tags
    cleaned = re.sub(r"\s*(?:with|\bat\b|in|\bhaving\b|\bfor\b).*$", "", cleaned, flags=re.IGNORECASE)
    return cleaned.strip()
```

### 3.3 Role Grammar Anchor Pattern

Match structured multi-word job titles against canonical industry structures:

```python
# Modifiers & Levels
LEVEL_PREFIXES = r"(?:Senior|Sr\.?|Lead|Staff|Principal|Associate|Junior|Jr\.?|Chief|VP\s+of|Director\s+of|Head\s+of)"

# Technical Domains
DOMAINS = (
    r"(?:Full[\s-]?Stack|Front[\s-]?End|Back[\s-]?End|Cloud|DevOps|Data|"
    r"AI/ML|Machine\s+Learning|Deep\s+Learning|BI|QA|Quality\s+Assurance|"
    r"Systems?|Platform|Security|Cyber\s?Security|Mobile|iOS|Android|"
    r"Embedded|Site\s+Reliability|SRE|Database|Network|Solutions?)"
)

# Core Occupational Roles
ROLES = (
    r"(?:Software\s+Engineer|Engineer|Developer|Architect|Analyst|Consultant|"
    r"Manager|Director|Specialist|Administrator|Scientist|Programmer|"
    r"Designer|Product\s+Manager|Project\s+Manager|Scrum\s+Master)"
)

ROLE_GRAMMAR_REGEX = re.compile(
    rf"^(?:{LEVEL_PREFIXES}\s+)?(?:{DOMAINS}\s+)?(?:{ROLES})$",
    re.IGNORECASE,
)
```

### 3.4 Discard Filter (Verbs & Degrees)

Explicitly discard matches that match known non-title grammatical patterns:
1. **Verb phrases**: Words ending in `"ed"`, `"ing"`, or modal auxiliary verbs (`"Able lead"`, `"Helped develop"`, `"Managing team"`).
2. **Degree patterns**: Lines containing `"Bachelor"`, `"Master"`, `"B.S."`, `"M.S."`, `"B.Tech"`, `"Ph.D."`, `"Degree in"`, `"University"`, `"College"`.
3. **Punctuation / sentence fragments**: Strings with more than 6 words or containing full stops inside text.

### 3.5 Title Selection Algorithm

1. Scan text line-by-line, tracking current section header context.
2. For each line, identify potential role phrases and strip noise prefixes.
3. Compute title score:
   $$\text{Score} = W_{\text{section}} \times (\text{Pattern Match Score}) - \text{Length Penalty}$$
   - Exact `ROLE_GRAMMAR_REGEX` match $\rightarrow$ Base Pattern Score = `1.0`.
   - Partial regex / dictionary match $\rightarrow$ Base Pattern Score = `0.6`.
   - Length Penalty $\rightarrow 0.05 \times (\text{word count} - 3)$ if word count $> 3$.
4. Select the title candidate with the highest score.
5. **Threshold Gate**:
   - If $\text{Score}_{\text{max}} \ge 0.50 \rightarrow$ accept as deterministic `current_title`.
   - If $\text{Score}_{\text{max}} < 0.50 \rightarrow$ mark title unconfident; trigger LLM fact extraction fallback or default to `"Candidate"`.

---

## 4. Verification & Testing Plan

### 4.1 Fast Unit Tests in `tests/test_deterministic_ner.py` (< 1s)
- **Prefix Stripping**: Verify `"Proven Backend Engineer with 7 years"` $\rightarrow$ extracts `"Backend Engineer"`.
- **Verb Exclusion**: Verify `"Able lead development team"` does NOT produce `"Able lead"`.
- **Education Discard**: Verify `"Bachelors in Computer Science and Engineering"` does NOT extract `"Engineering"`.
- **Section Priority**: Given a resume with `"Data Analyst"` in header and `"Senior Developer"` in education project, selects header `"Data Analyst"`.
- **Standard Roles**: Verify clean normalization for `Senior Software Engineer`, `Cloud DevOps Architect`, `Lead Data Scientist`.
