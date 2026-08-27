> 
> **ALREADY IMPLEMENTED** — This is already implemented and in codebase. Do NOT take this document as context / pending work unless user explicitly says otherwise.

# Search Accuracy Evaluation Harness

**Status:** `COMPLETED` (Issue #21)  
**Implemented In:** `tests/test_golden_eval.py`, `tests/fixtures/golden_search_set.json`  
**Baseline:** `tests/fixtures/golden_baseline.json`  

---

## 1. Overview & Problem Solved

To ensure ranking weight changes, reranker adjustments, and soft search filters tangibly improve search quality without regressions, an automated evaluation harness runs full local search pipelines against a versioned ground-truth dataset.

---

## 2. Dataset & Fixture Structure

Located in `tests/fixtures/`:
- `golden_search_set.json`:
  - `resumes`: Array of candidate resumes with IDs, contact info, and raw text.
  - `searches`: 20+ realistic recruiter queries mapped to expected candidate IDs in top-k.
- `golden_baseline.json`:
  - Records target baseline metrics: `recall_at_10`, `mrr`, and allowable `tolerance` (default 0.20).

---

## 3. Running & Updating Evaluations

### 3.1 Running Evaluation Gate
Run the evaluation test using real local embeddings and vector stores:
```powershell
uv run pytest tests/test_golden_eval.py -m evaluation --run-eval -s
```

### 3.2 Updating Recorded Baseline
When search algorithm improvements intentionally increase baseline metrics:
```powershell
uv run pytest tests/test_golden_eval.py -m evaluation --run-eval -s --update-baseline
```

---

## 4. Key Metrics Tracked

1. **Recall@10**: Percentage of expected relevant candidates present in the top 10 returned results.
2. **MRR (Mean Reciprocal Rank)**: Evaluates how close the top relevant candidate is to rank #1 ($\frac{1}{\text{rank}}$).
