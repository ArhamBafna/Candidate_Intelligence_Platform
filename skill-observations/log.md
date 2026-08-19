# Skill Observation Log

Observations captured during task-oriented work.

**Status key:** OPEN = not yet actioned | ACTIONED (YYYY-MM-DD) = skill updated/created | DECLINED (YYYY-MM-DD) = user decided not to pursue — resolved statuses always carry their resolution date

---

### Observation 1: Do not silently switch toolsets from approved plans

**Status:** OPEN
**Date:** 2026-08-19
**Session context:** End-to-end UI testing using playwriter instead of failing browser_subagent.
**Skill:** General execution
**Type:** open-source
**Phase/Area:** Execution

**Issue:** The playwriter script failed with an undefined state.page. Instead of waiting for the user to confirm they attached the extension or asking how they want to proceed, I planned to silently abandon the playwriter UI test and rewrite an API-based Python script, violating the "start to finish like a real user would" requirement and the user's explicit setup.

**Suggested improvement:** When an explicitly requested tool or approved plan encounters a failure, never silently pivot to a completely different methodology (like swapping a UI test for an API test) without asking the user.

**Principle:** When an agreed-upon methodology fails, report the failure and propose alternatives, but never silently execute a completely different methodology.
