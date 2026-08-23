# Search Accuracy Evaluation Harness

## Problem

Search accuracy changes ("more accurate") cannot be verified without ground truth. Any tuning of weights, rerankers, or embedding models today is guesswork.

## Goal

A small local evaluation harness that measures search quality and proves improvements.

## Design

### Golden set

- 20-40 real-world query -> expected-candidate pairs built from ingested test resumes.
- Each pair lists candidate IDs that MUST appear in top-k (recall targets) and optionally candidates that must NOT outrank them (precision targets).
- Stored as versioned JSON/YAML under `tests/fixtures/golden_search_set.*` so it doubles as a pytest fixture.

### Metrics

- Recall@5, Recall@10 — expected candidate found in top-k.
- MRR (mean reciprocal rank) — how high the right candidate lands.
- Precision@5 — junk above the fold.
- Optional nDCG@10 once graded relevance exists.

### Regression gate

- `uv run pytest tests/test_search_eval.py` runs the harness against the golden set with mocked/lightweight models by default; `--run-models` flag runs full local inference.
- Fails if recall@10 or MRR drop beyond tolerance vs stored baseline numbers.

## Success criteria

- Every search accuracy change lands with eval numbers before/after in the PR description.
