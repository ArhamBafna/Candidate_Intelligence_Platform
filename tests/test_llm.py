"""Guard tests: prompts moved into candidate_intelligence_platform.prompts must stay
byte-identical to the text that previously lived inline at the call sites.

These snapshots pin the exact bytes sent to the LLM. Rewording a prompt is a
deliberate behavior change and must update the snapshot here on purpose.
"""
from candidate_intelligence_platform.prompts import (
    build_fact_extraction_prompt,
    build_job_ad_distill_prompt,
    build_match_insight_prompt,
    build_consolidated_match_insight_prompt,
    build_batched_extraction_prompt,
    build_json_repair_prompt,
)


def test_fact_extraction_prompt_is_byte_identical() -> None:
    rendered = build_fact_extraction_prompt("Jane Doe\nSenior Engineer")
    expected = """
You are an expert fact-extraction engine for resumes. Extract all candidate facts into structured JSON.

Rules:
- Output category strictly as one of: PERSON, CONTACT, EMPLOYMENT, SKILL, EDUCATION, LOCATION.
- claim_key must be the descriptor/type (e.g., 'name', 'email', 'phone', 'title', 'company', 'skill', 'degree', 'institution', 'location').
- claim_value must contain the actual extracted text snippet (NEVER null or empty).
- confidence_score must be a float between 0.80 and 1.00.
- NEVER extract job titles, adjectives, or introductory phrases (e.g. 'Experienced Software Engineer', 'Self-Motivated Professional') as a PERSON name. If no personal name is explicitly present, omit the PERSON claim.

Return ONLY valid JSON matching this schema:
{
  "claims": [
    {
      "claim_category": "PERSON",
      "claim_key": "name",
      "claim_value": "Jane Doe",
      "confidence_score": 0.95
    },
    {
      "claim_category": "CONTACT",
      "claim_key": "email",
      "claim_value": "jane@example.com",
      "confidence_score": 0.98
    },
    {
      "claim_category": "EMPLOYMENT",
      "claim_key": "title",
      "claim_value": "Senior Software Engineer",
      "confidence_score": 0.95
    },
    {
      "claim_category": "SKILL",
      "claim_key": "skill",
      "claim_value": "Python",
      "confidence_score": 0.92
    },
    {
      "claim_category": "EDUCATION",
      "claim_key": "degree",
      "claim_value": "B.S. in Computer Science",
      "confidence_score": 0.90
    }
  ]
}

Text:
Jane Doe
Senior Engineer
"""
    assert rendered == expected


def test_match_insight_prompt_is_byte_identical() -> None:
    rendered = build_match_insight_prompt("Jane Doe profile", "python developer")
    expected = (
        "Given the candidate profile and resume text:\n"
        "Jane Doe profile\n\n"
        "Explain why this candidate is a good match for the search query: "
        "'python developer'. Output in bullet points in two sections: strengths and weaknesses (anything not matching/missing from the search query)."
    )
    assert rendered == expected


def test_match_insight_prompt_with_criteria() -> None:
    rendered = build_match_insight_prompt(
        "Jane Doe profile",
        "Python, React",
        city="San Francisco",
        job_title="Senior Engineer",
        min_years=5,
    )
    assert "Search Query / Skills: 'Python, React'" in rendered
    assert "Target Job Title: Senior Engineer" in rendered
    assert "Target City / Location: San Francisco" in rendered
    assert "Minimum Experience: 5 years" in rendered
    assert "Evaluate the candidate against all criteria above" in rendered


def test_match_insight_prompt_tolerates_braces_in_inputs() -> None:
    rendered = build_match_insight_prompt("{weird} {text}", "{query}")
    assert "{weird} {text}" in rendered
    assert "'{query}'" in rendered


def test_job_ad_distill_prompt_is_byte_identical() -> None:
    rendered = build_job_ad_distill_prompt("Hiring Backend Engineer in Berlin, 5+ years.")
    expected = """
You are a precise job-ad parser for a recruiting search engine.
Extract the structured requirements from the job advertisement below.

Return ONLY valid JSON with exactly these keys:
{
  "title": "<job title or null>",
  "skills": ["must-have skill", "..."],
  "min_yoe": <number of required years of experience or null>,
  "location": "<job location or null>"
}

Rules:
- Only include must-have requirements in "skills".
- "min_yoe" must be a plain number (e.g. 3 or 2.5) or null.
- Never invent values that are not stated in the ad.

Job advertisement:
Hiring Backend Engineer in Berlin, 5+ years.
"""
    assert rendered == expected


def test_consolidated_match_insight_prompt_is_byte_identical() -> None:
    rendered = build_consolidated_match_insight_prompt("Jane Doe profile", "python developer")
    expected = """
Given the candidate profile and resume text:
Jane Doe profile

Evaluate why this candidate is a good match for the following search criteria:
- Search Query / Skills: 'python developer'

Evaluate the candidate against all criteria above (job title, location/city, experience years, and required skills).
Please provide your evaluation in a clear, well-formatted markdown format.
Include the following sections:
- **Summary**: An executive summary of the match.
- **Strengths**: A bulleted list of strengths.
- **Weaknesses**: A bulleted list of weaknesses or missing required skills.
- **Match Confidence**: A score out of 10 or a percentage.
"""
    assert rendered == expected


def test_consolidated_match_insight_prompt_min_years_zero() -> None:
    rendered = build_consolidated_match_insight_prompt("Jane Doe profile", "python developer", min_years=0)
    assert "- Minimum Experience: 0 years" in rendered



def test_batched_extraction_prompt_is_byte_identical() -> None:
    rendered = build_batched_extraction_prompt(["Resume 1"])
    expected = """
You are an expert fact-extraction engine for resumes. Extract all candidate facts into structured JSON.
Return a list of results for each provided resume.
Return ONLY valid JSON matching this schema:
{
  "results": [
    {
      "claims": [
        ...
      ]
    }
  ]
}

Resumes:
Resume 1:
Resume 1
"""
    assert rendered == expected


def test_batched_extraction_prompt_multiple_resumes() -> None:
    rendered = build_batched_extraction_prompt(["Alice Doe\nPython Dev", "Bob Smith\nJava Dev"])
    assert "Resume 1:\nAlice Doe\nPython Dev" in rendered
    assert "Resume 2:\nBob Smith\nJava Dev" in rendered



def test_json_repair_prompt_is_byte_identical() -> None:
    rendered = build_json_repair_prompt('{"bad": json', "Expected quote")
    expected = """
You are a JSON repair engine.
The following JSON is malformed. Fix the syntax errors and return ONLY valid JSON matching the schema.
Do not add any explanations or markdown formatting outside the JSON block.

Malformed JSON:
{"bad": json

Error:
Expected quote
"""
    assert rendered == expected


def test_consolidated_match_insight_prompt_all_criteria() -> None:
    rendered = build_consolidated_match_insight_prompt(
        resume_text="Jane Doe profile",
        query="Python, AWS",
        city="London",
        job_title="Lead Architect",
        min_years=8,
    )
    assert "- Search Query / Skills: 'Python, AWS'" in rendered
    assert "- Target Job Title: Lead Architect" in rendered
    assert "- Target City / Location: London" in rendered
    assert "- Minimum Experience: 8 years" in rendered


def test_consolidated_match_insight_prompt_no_criteria() -> None:
    rendered = build_consolidated_match_insight_prompt(
        resume_text="Jane Doe profile",
        query="",
        city=None,
        job_title="",
        min_years=None,
    )
    assert "- (No specific criteria provided)" in rendered


def test_batched_extraction_prompt_three_resumes() -> None:
    resumes = [
        "Candidate One\nSkills: Go",
        "Candidate Two\nSkills: Rust",
        "Candidate Three\nSkills: TypeScript",
    ]
    rendered = build_batched_extraction_prompt(resumes)
    assert "Resume 1:\nCandidate One\nSkills: Go" in rendered
    assert "Resume 2:\nCandidate Two\nSkills: Rust" in rendered
    assert "Resume 3:\nCandidate Three\nSkills: TypeScript" in rendered


def test_json_repair_prompt_edge_cases() -> None:
    # Empty payload and empty error
    rendered_empty = build_json_repair_prompt("", "")
    assert "Malformed JSON:\n\n" in rendered_empty
    assert "Error:\n\n" in rendered_empty

    # Payload with special characters, quotes, and newlines
    payload = "{\n  \"key\": 'single quotes',\n  \"trailing\": 123,\n}"
    err = "Invalid character at line 2 col 10"
    rendered = build_json_repair_prompt(payload, err)
    assert payload in rendered
    assert err in rendered


# ---------------------------------------------------------------------------
# Chat Model Resolution & Fallback
# ---------------------------------------------------------------------------

import structlog
import pytest
from candidate_intelligence_platform.intelligence.chat_model import (
    chat_retry_candidates,
    normalize_model_name,
    resolve_chat_model,
    reset_chat_model_cache,
)

class FakeModelEntry:
    def __init__(self, name: str):
        self.model = name

class FakeListResponse:
    def __init__(self, names):
        self.models = [FakeModelEntry(n) for n in names]

def test_normalize_name_strips_tag():
    assert normalize_model_name("llama3.2:latest") == "llama3.2"
    assert normalize_model_name("LLaMA3.2 ") == "llama3.2"
    assert normalize_model_name("") == ""

def test_chat_retry_candidates_chain_and_dedup():
    assert chat_retry_candidates("mistral", "qwen2.5") == ["qwen2.5", "llama3.2"]
    assert chat_retry_candidates("mistral", "llama3.2") == ["llama3.2"]
    assert chat_retry_candidates("llama3.2", "llama3.2") == []
    assert chat_retry_candidates("mistral", "llama3.2", failed_model="qwen2.5") == ["llama3.2"]

def test_configured_chat_model_available(monkeypatch):
    monkeypatch.setattr("ollama.list", lambda: FakeListResponse(["llama3.2:latest", "mistral:7b"]))
    resolved = resolve_chat_model()
    assert resolved == "llama3.2"

def test_invalid_chat_model_retries_with_llama32_fallback(monkeypatch):
    monkeypatch.setenv("CIP_LLM_MODEL", "not-installed-model")
    monkeypatch.setattr("ollama.list", lambda: FakeListResponse(["llama3.2:latest"]))
    reset_chat_model_cache()
    resolved = resolve_chat_model()
    assert resolved == "llama3.2"

def test_total_chat_failure_returns_none(monkeypatch):
    monkeypatch.setenv("CIP_LLM_MODEL", "ghost-model")
    monkeypatch.setattr("ollama.list", lambda: FakeListResponse(["mistral:7b"]))
    reset_chat_model_cache()
    resolved = resolve_chat_model()
    assert resolved is None

def test_ollama_probe_failure_treated_as_no_models(monkeypatch):
    monkeypatch.setattr("ollama.list", lambda: (_ for _ in ()).throw(RuntimeError("connection refused")))
    reset_chat_model_cache()
    resolved = resolve_chat_model()
    assert resolved is None


# ---------------------------------------------------------------------------
# Local LLM Fallback & Inference Extraction
# ---------------------------------------------------------------------------

from candidate_intelligence_platform.extraction.local_llm_fallback import (
    extract_inferences,
    batched_extract_inferences,
)

def test_extract_inferences(monkeypatch):
    text = "Led a team of 5 engineers building distributed systems in Go."
    class MockMessage:
        content = '{"claims": [{"claim_category": "SKILL", "claim_key": "Go", "claim_value": "Go", "confidence_score": 0.9}]}'
    class MockResponse:
        message = MockMessage()
    import ollama
    monkeypatch.setattr(ollama, "chat", lambda *args, **kwargs: MockResponse())
    facts = extract_inferences(text)
    assert len(facts) == 1
    assert facts[0]['claim_key'] == 'Go'
    assert facts[0]['source_type'] == 'AI_INFERENCE'

def test_extract_inferences_malformed_json(monkeypatch):
    class MockMessage:
        content = '{"claims": [broken json'
    class MockResponse:
        message = MockMessage()
    import ollama
    monkeypatch.setattr(ollama, "chat", lambda *args, **kwargs: MockResponse())
    facts = extract_inferences("Text")
    assert len(facts) == 0

def test_extract_inferences_exception(monkeypatch):
    import ollama
    monkeypatch.setattr(ollama, "chat", lambda *args, **kwargs: (_ for _ in ()).throw(ValueError("failed")))
    facts = extract_inferences("Text")
    assert len(facts) == 0

def test_batched_extract_inferences(monkeypatch):
    class MockMessage:
        content = '{"claims": [{"claim_category": "SKILL", "claim_key": "Python", "claim_value": "Python", "confidence_score": 0.95}]}'
    class MockResponse:
        message = MockMessage()
    import ollama
    monkeypatch.setattr(ollama, "chat", lambda *args, **kwargs: MockResponse())
    texts = ["Resume text 1", "Resume text 2"]
    results = batched_extract_inferences(texts)
    assert len(results) == 2
    assert results[0][0]["claim_key"] == "Python"


# ---------------------------------------------------------------------------
# Job Ad Distiller
# ---------------------------------------------------------------------------

import json
from candidate_intelligence_platform.search import job_ad_distiller as jad
from candidate_intelligence_platform.search.job_ad_distiller import (
    JobAdRecipe,
    build_search_dsl,
    distill_job_ad,
    looks_like_job_ad,
)

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
    return lambda **kwargs: FakeResponse()

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
    assert {"kubernetes", "postgres", "airflow"} <= {s.lower() for s in recipe.skills}
    assert recipe.min_yoe >= 5.0


def test_build_search_dsl_round_trips_through_parser():
    from candidate_intelligence_platform.search.ast_parser import parse_query_to_sql
    recipe = JobAdRecipe(
        title="Data Engineer",
        skills=["python", "sql"],
        min_yoe=2.5,
        location="New York",
        summary="Role: Data Engineer.",
        source="ai",
    )
    dsl = build_search_dsl(recipe)
    sql, params, clean = parse_query_to_sql(dsl)
    assert params["title"] == "Data Engineer"
    assert params["location"] == "New York"
    assert params["yoe"] == 2.5


# ---------------------------------------------------------------------------
# Model Fallbacks
# ---------------------------------------------------------------------------

class _SentinelModel:
    pass


def test_model_fallbacks_from_settings(monkeypatch):
    from config.settings import get_settings
    import candidate_intelligence_platform.intelligence.embeddings as emb
    from candidate_intelligence_platform.intelligence.embeddings import DEFAULT_EMBEDDING_MODEL
    import candidate_intelligence_platform.search.reranker as rer
    from candidate_intelligence_platform.search.reranker import DEFAULT_RERANKER_MODEL

    get_settings.cache_clear()
    monkeypatch.setenv("CIP_EMBEDDING_MODEL", "not-a-real-model")
    emb_calls = []

    def fake_load_emb(model_name):
        emb_calls.append(model_name)
        if model_name == "not-a-real-model":
            raise RuntimeError("model not found")
        return _SentinelModel()

    monkeypatch.setattr("candidate_intelligence_platform.intelligence.embeddings._load_text_embedding", fake_load_emb)
    emb._embedding_model = None
    emb._embedding_model_name = None
    model = emb._get_embedding_model()
    assert emb_calls == ["not-a-real-model", DEFAULT_EMBEDDING_MODEL]
    assert emb.get_embedding_model_name() == DEFAULT_EMBEDDING_MODEL

    get_settings.cache_clear()
    monkeypatch.setenv("CIP_RERANKER_MODEL", "not-a-real-reranker")
    rer_calls = []

    def fake_load_rer(model_name):
        rer_calls.append(model_name)
        if model_name == "not-a-real-reranker":
            raise RuntimeError("model not found")
        return _SentinelModel()

    monkeypatch.setattr("candidate_intelligence_platform.search.reranker._load_text_cross_encoder", fake_load_rer)
    rer._reranker_model = None
    rer._reranker_model_name = None
    model_rer = rer._get_reranker()
    assert rer_calls == ["not-a-real-reranker", DEFAULT_RERANKER_MODEL]
    assert rer.get_reranker_model_name() == DEFAULT_RERANKER_MODEL

    # Clean up singletons so subsequent tests get fresh models
    emb._embedding_model = None
    emb._embedding_model_name = None
    rer._reranker_model = None
    rer._reranker_model_name = None
    get_settings.cache_clear()


# ---------------------------------------------------------------------------
# Live Ollama Standalone (Opt-in)
# ---------------------------------------------------------------------------

@pytest.mark.ollama
def test_live_ollama_extraction():
    pass

