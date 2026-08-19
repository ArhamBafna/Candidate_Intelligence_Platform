import pytest
import structlog
from candidate_intelligence_platform.search.hybrid_searcher import search_candidates, execute_vector_search
from candidate_intelligence_platform.extraction.local_llm_fallback import extract_inferences

def test_vector_search_failure_logs_ai_warning(monkeypatch):
    with structlog.testing.capture_logs() as cap_logs:
        # Pass an invalid vector_db or force exception in generate_single_embedding
        def mock_embeddings(text):
            raise RuntimeError("Embedding model server timeout")
            
        monkeypatch.setattr("candidate_intelligence_platform.search.hybrid_searcher.generate_single_embedding", mock_embeddings)
        
        warnings = []
        ranks = execute_vector_search("python developer", ["cid-1"], vector_db=None, warnings=warnings)
        assert ranks == {}
        
        events = [log for log in cap_logs if log.get("event") == "ai_vector_search_failed"]
        assert len(events) == 1
        assert events[0]["error"] == "Embedding model server timeout"

def test_llm_extraction_failure_logs_ai_warning(monkeypatch):
    with structlog.testing.capture_logs() as cap_logs:
        def mock_chat(*args, **kwargs):
            raise RuntimeError("Ollama connection refused")
            
        import ollama
        monkeypatch.setattr(ollama, "chat", mock_chat)
        
        facts = extract_inferences("Some resume text")
        assert facts == []
        
        events = [log for log in cap_logs if log.get("event") == "ai_llm_extraction_failed"]
        assert len(events) == 1
        assert "Ollama connection refused" in events[0]["error"]

def test_llm_claim_value_null_logs_warning_and_repairs(monkeypatch):
    """Test when LLM returns null claim_value and entity in claim_key."""
    with structlog.testing.capture_logs() as cap_logs:
        class MockMessage:
            content = '{"claims": [{"claim_category": "SKILL", "claim_key": "Go", "claim_value": null, "confidence_score": 0.0}]}'
            
        class MockResponse:
            message = MockMessage()
            
        def mock_chat(*args, **kwargs):
            return MockResponse()
            
        import ollama
        monkeypatch.setattr(ollama, "chat", mock_chat)
        
        facts = extract_inferences("Experience in Go")
        assert len(facts) == 1
        assert facts[0]["claim_category"] == "SKILL"
        assert facts[0]["claim_key"] == "skill"
        assert facts[0]["claim_value"] == "Go"
        assert facts[0]["confidence_score"] == 0.90
        
        repair_logs = [log for log in cap_logs if log.get("event") == "ai_llm_claim_value_missing_repaired"]
        assert len(repair_logs) == 1
        
        score_logs = [log for log in cap_logs if log.get("event") == "ai_llm_invalid_confidence_score"]
        assert len(score_logs) == 1
