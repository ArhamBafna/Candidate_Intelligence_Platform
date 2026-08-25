"""Tests for candidate_intelligence_platform/search/job_ad_distiller.py

Paste-a-job-ad mode (issue #23). All chat AI calls are mocked; suite stays fast.
"""
import json

import pytest

from candidate_intelligence_platform.search import job_ad_distiller as jad
from candidate_intelligence_platform.search.job_ad_distiller import (
    JobAdRecipe,
    build_search_dsl,
    distill_job_ad,
    looks_like_job_ad,
)
from candidate_intelligence_platform.search.ast_parser import parse_query_to_sql

LONG_AD = (
    "Data Engineer\n\n"
    "We are hiring a Data Engineer to join our analytics platform team.\n\n"
    "Responsibilities:\n"
    "- Build pipelines on kubernetes clusters\n"
    "- Model data in postgres warehouses\n"
    "- Orchestrate jobs with airflow\n\n"
    "Requirements:\n"
    "- At least 5+ years of experience building data platforms\n"
    "- Deep knowledge of python and sql\n"
    "- Experience with kubernetes, postgres, airflow\n\n"
    "Location: NYC\n"
    "We offer a competitive salary and great benefits.\n"
)


def _ai_response(payload: dict):
    class FakeMessage:
        content = json.dumps(payload)

    class FakeResponse:
        message = FakeMessage()

    def fake_chat(**kwargs):
        return FakeResponse()

    return fake_chat


def test_looks_like_job_ad_threshold():
    assert not looks_like_job_ad("python dev nyc")
    assert looks_like_job_ad("x" * (jad.JOB_AD_MIN_CHARS + 1))


def test_ai_distill_parses_recipe(monkeypatch):
    monkeypatch.setattr(jad, "resolve_chat_model", lambda force_refresh=False: "llama3.2")
    monkeypatch.setattr(
        "ollama.chat",
        _ai_response({
            "title": "Data Engineer",
            "skills": ["python", "sql", "airflow"],
            "min_yoe": 5,
            "location": "NYC",
        }),
    )

    recipe = distill_job_ad(LONG_AD)

    assert recipe.source == "ai"
    assert recipe.title == "Data Engineer"
    assert recipe.skills == ["python", "sql", "airflow"]
    assert recipe.min_yoe == 5.0
    assert recipe.location == "NYC"
    assert recipe.warnings == []
    assert len(recipe.summary) <= jad.SUMMARY_MAX_CHARS
    assert "Data Engineer" in recipe.summary


def test_ai_garbage_json_falls_back_to_heuristics(monkeypatch):
    monkeypatch.setattr(jad, "resolve_chat_model", lambda force_refresh=False: "llama3.2")

    class BadMessage:
        content = "not json at all"

    class BadResponse:
        message = BadMessage()

    monkeypatch.setattr("ollama.chat", lambda **kwargs: BadResponse())

    recipe = distill_job_ad(LONG_AD)

    assert recipe.source == "fallback"
    assert recipe.min_yoe >= 5.0
    assert any("unavailable" in w for w in recipe.warnings)


def test_ai_unavailable_uses_non_ai_extraction(monkeypatch):
    monkeypatch.setattr(jad, "resolve_chat_model", lambda force_refresh=False: None)

    recipe = distill_job_ad(LONG_AD)

    assert recipe.source == "fallback"
    lowered_skills = {s.lower() for s in recipe.skills}
    assert {"kubernetes", "postgres", "airflow"} <= lowered_skills
    assert recipe.min_yoe >= 5.0
    assert recipe.location == "NYC"
    assert any("unavailable" in w for w in recipe.warnings)


def test_nothing_useful_searches_raw_text_with_warning(monkeypatch):
    monkeypatch.setattr(jad, "resolve_chat_model", lambda force_refresh=False: None)
    monkeypatch.setattr(jad, "_fallback_distill", lambda text: None)

    recipe = distill_job_ad(LONG_AD)

    assert recipe.source == "raw"
    assert recipe.summary.startswith("Data Engineer")
    assert any("searching the pasted text directly" in w for w in recipe.warnings)


# PR #25 review: a full sentence containing a title must never become the
# strict equality filter.
SENTENCE_AD = (
    "About our company\n"
    "We are hiring a Senior Data Engineer to join our team,\n"
    "working on analytics and data platforms.\n\n"
    "Requirements:\n"
    "- At least 5+ years of experience with python and sql\n"
    "- Experience with kubernetes and airflow\n"
)


def test_fallback_title_extracts_phrase_not_sentence(monkeypatch):
    monkeypatch.setattr(jad, "resolve_chat_model", lambda force_refresh=False: None)

    recipe = distill_job_ad(SENTENCE_AD)

    assert recipe.source == "fallback"
    assert recipe.title == "Senior Data Engineer"


def test_fallback_sentence_title_dsl_stays_clean(monkeypatch):
    monkeypatch.setattr(jad, "resolve_chat_model", lambda force_refresh=False: None)

    recipe = distill_job_ad(SENTENCE_AD)
    sql, params = parse_query_to_sql(build_search_dsl(recipe))

    assert params["title"] == "Senior Data Engineer"


def test_build_search_dsl_round_trips_through_parser():
    recipe = JobAdRecipe(
        title="Data Engineer",
        skills=["python", "sql"],
        min_yoe=2.5,
        location="New York",
        summary="Role: Data Engineer. Skills: python, sql.",
        source="ai",
    )

    dsl = build_search_dsl(recipe)
    sql, params = parse_query_to_sql(dsl)

    assert params["title"] == "Data Engineer"
    assert params["location"] == "New York"
    assert params["yoe"] == 2.5
    fts_lower = params["fts_query"].lower()
    assert "python" in fts_lower
    assert "sql" in fts_lower
    # FTS query now preserves extracted structured filter text (Issue #36)
    assert "data engineer" in fts_lower
    assert "new york" in fts_lower


def test_recipe_metadata_shape():
    recipe = JobAdRecipe(
        title="T", skills=["s"], min_yoe=None, location=None,
        summary="sum", source="fallback", warnings=["w1"],
    )
    meta = recipe.to_metadata()
    assert set(meta) == {"title", "skills", "min_yoe", "location", "summary", "source", "warnings"}
