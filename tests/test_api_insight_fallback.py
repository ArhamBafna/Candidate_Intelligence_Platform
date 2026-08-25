import json
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from storage.db_models import Candidate


@pytest.fixture
def candidate_id(db_session: Session) -> str:
    cid = str(uuid.uuid4())
    db_session.add(Candidate(id=cid, first_name="Insight", last_name="Test", availability_status="ACTIVE"))
    db_session.commit()
    return cid


def _stream_insight(client: TestClient, cid: str) -> str:
    with client.stream("GET", f"/candidates/{cid}/insight", params={"query": "python"}) as response:
        return "".join(response.iter_text())


def _parse_events(body: str) -> list[dict]:
    events = []
    for line in body.splitlines():
        if line.startswith("data: "):
            events.append(json.loads(line[len("data: "):]))
    return events


def test_insight_streams_tokens_when_model_available(client: TestClient, candidate_id: str, monkeypatch):
    monkeypatch.setattr(
        "api.routes.candidates.resolve_chat_model",
        lambda force_refresh=False: "llama3.2",
    )

    async def fake_stream(prompt, model_name, **kwargs):
        assert model_name == "llama3.2"
        for tok in ["hello ", "world"]:
            yield tok

    monkeypatch.setattr("api.routes.candidates.stream_ollama_generate", fake_stream)

    body = _stream_insight(client, candidate_id)
    events = _parse_events(body)

    tokens = [e["token"] for e in events if "token" in e]
    assert "".join(tokens) == "hello world"
    assert not any(e.get("error") for e in events)


def test_insight_emits_visible_message_when_no_chat_model(client: TestClient, candidate_id: str, monkeypatch):
    monkeypatch.setattr(
        "api.routes.candidates.resolve_chat_model",
        lambda force_refresh=False: None,
    )

    async def must_not_run(prompt, model_name, **kwargs):
        raise AssertionError("ollama stream should not be called when no model is available")
        yield  # pragma: no cover

    monkeypatch.setattr("api.routes.candidates.stream_ollama_generate", must_not_run)

    body = _stream_insight(client, candidate_id)
    events = _parse_events(body)

    errors = [e for e in events if e.get("error") == "AI_EXPLANATION_UNAVAILABLE"]
    assert len(errors) == 1
    assert "taking a break right now" in errors[0]["message"].lower()


def test_insight_invalid_model_retries_fallback_before_giving_up(client: TestClient, candidate_id: str, monkeypatch):
    monkeypatch.setenv("CIP_LLM_MODEL", "broken-model")
    monkeypatch.setattr(
        "api.routes.candidates.resolve_chat_model",
        lambda force_refresh=False: "broken-model",
    )
    called_models = []

    async def fake_stream(prompt, model_name, **kwargs):
        called_models.append(model_name)
        if model_name == "broken-model":
            raise RuntimeError("model 'broken-model' not found")
        yield "recovered"

    monkeypatch.setattr("api.routes.candidates.stream_ollama_generate", fake_stream)

    body = _stream_insight(client, candidate_id)
    events = _parse_events(body)

    tokens = [e["token"] for e in events if "token" in e]
    assert "".join(tokens) == "recovered"
    assert called_models == ["broken-model", "llama3.2"]
    assert not any(e.get("error") for e in events)


def test_insight_total_failure_surfaces_visible_message(client: TestClient, candidate_id: str, monkeypatch):
    monkeypatch.setattr(
        "api.routes.candidates.resolve_chat_model",
        lambda force_refresh=False: "llama3.2",
    )

    async def always_fails(prompt, model_name, **kwargs):
        raise RuntimeError("ollama connection refused")
        yield  # pragma: no cover

    monkeypatch.setattr("api.routes.candidates.stream_ollama_generate", always_fails)

    body = _stream_insight(client, candidate_id)
    events = _parse_events(body)

    errors = [e for e in events if e.get("error") == "AI_EXPLANATION_UNAVAILABLE"]
    assert len(errors) == 1
    assert "taking a break right now" in errors[0]["message"].lower()


def test_insight_passes_criteria_to_prompt(client: TestClient, candidate_id: str, monkeypatch):
    monkeypatch.setattr(
        "api.routes.candidates.resolve_chat_model",
        lambda force_refresh=False: "llama3.2",
    )

    captured_prompt = []

    async def fake_stream(prompt, model_name, **kwargs):
        captured_prompt.append(prompt)
        yield "all good"

    monkeypatch.setattr("api.routes.candidates.stream_ollama_generate", fake_stream)

    with client.stream(
        "GET",
        f"/candidates/{candidate_id}/insight",
        params={
            "query": "python",
            "city": "Boston",
            "job_title": "Lead Architect",
            "min_years": 8,
        },
    ) as response:
        body = "".join(response.iter_text())

    events = _parse_events(body)
    tokens = [e["token"] for e in events if "token" in e]
    assert "".join(tokens) == "all good"
    assert len(captured_prompt) == 1
    assert "Target City / Location: Boston" in captured_prompt[0]
    assert "Target Job Title: Lead Architect" in captured_prompt[0]
    assert "Minimum Experience: 8.0 years" in captured_prompt[0] or "Minimum Experience: 8 years" in captured_prompt[0]

