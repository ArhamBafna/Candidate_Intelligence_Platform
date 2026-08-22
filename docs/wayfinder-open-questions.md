# Wayfinder run — open questions for owner

Map [#4](https://github.com/ArhamBafna/Candidate_Intelligence_Platform/issues/4) completed 2026-08-22: all six tickets resolved, build-ready spec posted as [#12](https://github.com/ArhamBafna/Candidate_Intelligence_Platform/issues/12). **All questions answered by owner 2026-08-22** (sign-off comment on the map); spec amended same day. Kept for the record.

1. **AI-stage label timing** — ANSWERED: after-only is fine. SSE stays `ENTITY_RESOLUTION` during inference; `AI_EXTRACTION` fires post-hoc. D13's single-assess rule stands.

2. **Non-resume website wording** — ANSWERED: locked as proposed. *"This file doesn't look like a resume: {reason}. Nothing was saved."*

3. **Settings field names** (#6) — ANSWERED: names fine. `extraction_confidence_threshold` (0.40), `entity_res_auto_merge_threshold` (0.85), `entity_res_review_threshold` (0.70).

4. **REVIEW-band UI hint** (#6 Q3) — ANSWERED: owner pulled it INTO this round. Spec #12 now includes a "Possible duplicate?" chip on the upload queue for REVIEW outcomes, linking `matched_candidate_id`. Map out-of-scope line amended accordingly.

5. **Audit row semantics for MERGE** (#8) — ANSWERED: accepted (same id twice in the two NOT NULL slots; `resolution_type` disambiguates; no migration).

6. **Prototype commit on the work branch** (#6) — ANSWERED: accepted where it is (`docs/prototypes/intake_module_sketch.py`, 9b1ef20).

Nothing remains open; implementation on `refactor/unify-resume-intake` can start against spec #12.
