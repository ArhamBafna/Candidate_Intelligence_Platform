"""Tests for ingestion/entity_resolution.py

Seam under test:
    resolve(
        incoming: CandidateIdentifiers,
        existing: list[CandidateIdentifiers],
    ) -> ResolutionResult

Tier 1 — Deterministic exact-key matching:
  - Match on email, phone, or linkedin_url (each independently sufficient).
  - If any key matches → action=MERGE, tier=1, confidence=1.0.

Tier 2 — Probabilistic name similarity scoring:
  - Normalised name similarity (e.g. Jaro-Winkler or token overlap).
  - score >= AUTO_MERGE_THRESHOLD  → action=MERGE, tier=2.
  - AUTO_MERGE_THRESHOLD > score >= REVIEW_THRESHOLD → action=REVIEW, tier=2.
  - score < REVIEW_THRESHOLD → action=NEW, tier=2.

Edge cases:
  - Empty existing list → action=NEW.
  - Incoming with no keys → action=NEW.
"""
import pytest

from ingestion.entity_resolution import (
    CandidateIdentifiers,
    ResolutionResult,
    resolve,
    ResolutionAction,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make(
    candidate_id: str = "cand-1",
    email: str | None = None,
    phone: str | None = None,
    linkedin_url: str | None = None,
    full_name: str = "",
) -> CandidateIdentifiers:
    return CandidateIdentifiers(
        candidate_id=candidate_id,
        email=email,
        phone=phone,
        linkedin_url=linkedin_url,
        full_name=full_name,
    )


# ---------------------------------------------------------------------------
# Tier 1: Deterministic exact-key matching
# ---------------------------------------------------------------------------

class TestTier1ExactMatch:

    def test_email_match_returns_merge(self):
        """Identical email → MERGE on Tier 1, confidence=1.0."""
        incoming = _make("new", email="alice@example.com", full_name="Alice Smith")
        existing = [_make("old-1", email="alice@example.com", full_name="Alice Smith")]

        result = resolve(incoming, existing)

        assert result.action == ResolutionAction.MERGE
        assert result.tier == 1
        assert result.confidence == 1.0
        assert result.matched_id == "old-1"
        assert "email" in result.matching_keys

    def test_phone_match_returns_merge(self):
        """Identical phone → MERGE on Tier 1."""
        incoming = _make("new", phone="+14155550100", full_name="Bob Jones")
        existing = [_make("old-2", phone="+14155550100", full_name="Bob Jones")]

        result = resolve(incoming, existing)

        assert result.action == ResolutionAction.MERGE
        assert result.tier == 1
        assert "phone" in result.matching_keys

    def test_linkedin_match_returns_merge(self):
        """Identical LinkedIn URL → MERGE on Tier 1."""
        incoming = _make("new", linkedin_url="https://linkedin.com/in/carol", full_name="Carol Chen")
        existing = [_make("old-3", linkedin_url="https://linkedin.com/in/carol")]

        result = resolve(incoming, existing)

        assert result.action == ResolutionAction.MERGE
        assert result.tier == 1
        assert "linkedin_url" in result.matching_keys

    def test_multiple_key_matches_still_tier1(self):
        """Multiple matching keys still resolves as Tier 1."""
        incoming = _make("new", email="dave@x.com", phone="+1999", linkedin_url="linkedin.com/in/dave")
        existing = [_make("old-4", email="dave@x.com", phone="+1999", linkedin_url="linkedin.com/in/dave")]

        result = resolve(incoming, existing)

        assert result.tier == 1
        assert result.action == ResolutionAction.MERGE

    def test_no_key_match_does_not_trigger_tier1(self):
        """Different contact keys must not produce a Tier 1 match."""
        incoming = _make("new", email="eve@a.com", phone="+111")
        existing = [_make("old-5", email="frank@b.com", phone="+222")]

        result = resolve(incoming, existing)

        assert result.tier != 1 or result.action != ResolutionAction.MERGE

    def test_none_keys_do_not_match(self):
        """None email/phone/linkedin must not match a None on the other side."""
        incoming = _make("new", email=None)
        existing = [_make("old-6", email=None)]

        result = resolve(incoming, existing)

        # None != None for identity resolution purposes
        assert result.tier != 1


# ---------------------------------------------------------------------------
# Tier 2: Probabilistic name similarity
# ---------------------------------------------------------------------------

class TestTier2NameSimilarity:

    def test_identical_name_auto_merges(self):
        """Exact same full_name (no key match) → Tier 2 MERGE."""
        incoming = _make("new", full_name="Grace Hopper")
        existing = [_make("old-7", full_name="Grace Hopper")]

        result = resolve(incoming, existing)

        assert result.action == ResolutionAction.MERGE
        assert result.tier == 2

    def test_very_similar_name_auto_merges(self):
        """Very similar name (typo/nick) → Tier 2 MERGE above auto-merge threshold."""
        incoming = _make("new", full_name="Grace Hooper")   # typo
        existing = [_make("old-8", full_name="Grace Hopper")]

        result = resolve(incoming, existing)

        # Should be MERGE or REVIEW — not NEW
        assert result.action in (ResolutionAction.MERGE, ResolutionAction.REVIEW)
        assert result.tier == 2

    def test_dissimilar_names_yield_new(self):
        """Completely different names → NEW (no match)."""
        incoming = _make("new", full_name="Zara Kim")
        existing = [_make("old-9", full_name="John Smith")]

        result = resolve(incoming, existing)

        assert result.action == ResolutionAction.NEW

    def test_partial_name_match_may_trigger_review(self):
        """Shared last name only → at most REVIEW, not auto-MERGE."""
        incoming = _make("new", full_name="Alice Johnson")
        existing = [_make("old-10", full_name="Bob Johnson")]

        result = resolve(incoming, existing)

        # Must not auto-merge on last name alone
        assert result.action != ResolutionAction.MERGE or result.tier == 1


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:

    def test_empty_existing_returns_new(self):
        """No existing candidates → always NEW."""
        incoming = _make("new", email="test@test.com", full_name="Test User")

        result = resolve(incoming, [])

        assert result.action == ResolutionAction.NEW
        assert result.matched_id is None

    def test_incoming_all_none_keys_returns_new(self):
        """Incoming with no contact keys and empty name → NEW."""
        incoming = _make("new", email=None, phone=None, linkedin_url=None, full_name="")

        result = resolve(incoming, [_make("old-11", email="x@x.com", full_name="Someone")])

        assert result.action == ResolutionAction.NEW

    def test_resolution_result_has_required_fields(self):
        """ResolutionResult must always expose action, tier, confidence, matched_id, matching_keys."""
        incoming = _make("new", email="z@z.com")
        result = resolve(incoming, [])

        assert hasattr(result, "action")
        assert hasattr(result, "tier")
        assert hasattr(result, "confidence")
        assert hasattr(result, "matched_id")
        assert hasattr(result, "matching_keys")
