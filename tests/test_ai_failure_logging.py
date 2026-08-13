import pytest
import structlog
from candidate_intelligence_platform.search.hybrid_searcher import search_candidates, execute_vector_search
from candidate_intelligence_platform.extraction.local_llm_fallback import extract_inferences

def test_vector_search_failure_logs_ai_warning(monkeypatch):
    with structlog.testing.capture_logs() as cap_logs:
        # Pass an invalid vector_db or force exception in generate_embeddings
        def mock_embeddings(texts):
            raise RuntimeError("Embedding model server timeout")
            
        monkeypatch.setattr("candidate_intelligence_platform.search.hybrid_searcher.generate_embeddings", mock_embeddings)
        
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
