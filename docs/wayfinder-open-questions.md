# Wayfinder run — open questions for owner

Map [#4](https://github.com/ArhamBafna/Candidate_Intelligence_Platform/issues/4) completed 2026-08-22: all six tickets resolved, build-ready spec posted as [#12](https://github.com/ArhamBafna/Candidate_Intelligence_Platform/issues/12). You were absent, so HITL tickets were resolved as working proposals. Nothing blocks the build; these are the calls you may want to veto or refine before/after implementation.

1. **AI-stage label timing** (#6 Q1, echoed in #7/#12): keeping `assess_tier1` to exactly one run (D13) means the pipeline can't know before extraction whether the local LLM will fire, so SSE shows `ENTITY_RESOLUTION` during inference and an `AI_EXTRACTION` event only after it completes. Today the AI label appears *before* the slow Ollama call. Acceptable tradeoff, or allow a cheap second assess on cached facts to keep the pre-label?

2. **Non-resume website wording** (#7): direction locked ("This file doesn't look like a resume: {reason}. Nothing was saved."). Exact copy is yours to wordsmith.

3. **Settings field names** (#6): `extraction_confidence_threshold` (0.40), `entity_res_auto_merge_threshold` (0.85), `entity_res_review_threshold` (0.70). Names deliberately avoid the deleted `entity_resolution_auto_merge_threshold` (0.92) so stale env vars can't misfire. Confirm or rename before slice 1 lands (env-var rename after ship is annoying).

4. **REVIEW-band UI hint** (#6 Q3): D2 creates a separate candidate and logs an audit row; response gains additive fields (`resolution_action`, `matched_candidate_id`). A future "possible duplicate" hint in the UI is out of scope now — flag if you want it ticketed later.

5. **Audit row semantics for MERGE** (#8): `merged_candidate_id` repeats the surviving id on MERGE rows (column is NOT NULL; no second row exists). If that reads wrong to you, alternatives require a schema migration — currently ruled out.

6. **Prototype commit on the work branch** (#6): `docs/prototypes/intake_module_sketch.py` committed straight to `refactor/unify-resume-intake` (9b1ef20) so the issue had a linkable asset. Say the word if you'd rather it live elsewhere.
