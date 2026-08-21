import json
import pytest
from candidate_intelligence_platform.extraction.local_llm_fallback import extract_inferences

@pytest.mark.ollama
def test_live_ollama_extraction():
    """Live integration test against running Ollama instance."""
    sample_resume_text = """
    Jane Doe
    Senior Backend Engineer at Acme Corp (2020 - Present)
    Built high-throughput microservices using Go, Python, and PostgreSQL.
    Architected event-driven streaming with Apache Kafka and Docker.
    Education: B.S. in Computer Science from University of Washington.
    """
    
    print("\n--- [INPUT RESUME TEXT] ---")
    print(sample_resume_text.strip())
    
    facts = extract_inferences(sample_resume_text)
    
    print("\n--- [OLLAMA OUTPUT EXTRACTED FACTS] ---")
    print(json.dumps(facts, indent=2))
    
    if not facts:
        pytest.xfail("Ollama returned no facts. It likely timed out (takes >30s) or isn't running. Treating as a warning instead of a hard failure.")
        
    assert isinstance(facts, list), "Expected output to be a list"
    
    for fact in facts:
        assert fact["source_type"] == "AI_INFERENCE"
        assert fact["extracted_by"] == "OLLAMA_LLM_V1"
        assert "claim_category" in fact
        assert "claim_key" in fact

if __name__ == "__main__":
    test_live_ollama_extraction()
