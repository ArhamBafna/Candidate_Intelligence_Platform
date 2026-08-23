"""Tests for candidate_intelligence_platform/intelligence/explainer.py

Focus (issue #18):
  - Missing rerank score degrades gracefully: percentage derived from RRF,
    never a fabricated constant.
"""
import pytest

from candidate_intelligence_platform.intelligence.explainer import MatchParameters, build_match_rationale


def _params(**overrides) -> MatchParameters:
    defaults = dict(candidate_id="c1", rank=1, rrf_score=0.0, rerank_score=None)
    defaults.update(overrides)
    return MatchParameters(**defaults)


def test_missing_rerank_score_derives_percentage_from_rrf():
    params = _params(rrf_score=(2.0 / 61.0))
    rationale = build_match_rationale(params)

    assert rationale["rerank_score"] is None
    assert rationale["match_percentage"] == pytest.approx(100.0)


def test_missing_rerank_score_never_fabricates_50_percent():
    for rrf in (0.001, 0.01, 0.02, 0.03):
        rationale = build_match_rationale(_params(rrf_score=rrf))
        assert rationale["match_percentage"] != 50.0


def test_zero_scores_yield_zero_percentage():
    rationale = build_match_rationale(_params())
    assert rationale["match_percentage"] == 0.0


def test_extreme_rerank_score_does_not_crash_or_default_to_50():
    huge = build_match_rationale(_params(rerank_score=1e9))
    tiny = build_match_rationale(_params(rerank_score=-1e9))

    assert huge["match_percentage"] == pytest.approx(100.0)
    assert tiny["match_percentage"] == pytest.approx(0.0)
    assert tiny["match_percentage"] != 50.0


def test_valid_rerank_score_sigmoid_mapped():
    zero = build_match_rationale(_params(rerank_score=0.0))
    assert zero["match_percentage"] == pytest.approx(50.0, abs=0.1)

    strong = build_match_rationale(_params(rerank_score=4.0))
    weak = build_match_rationale(_params(rerank_score=-4.0))
    assert strong["match_percentage"] > weak["match_percentage"]
