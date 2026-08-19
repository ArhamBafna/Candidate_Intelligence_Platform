import pytest
from candidate_intelligence_platform.extraction.local_llm_fallback import extract_inferences

def test_extract_inferences(monkeypatch):
    text = "Led a team of 5 engineers building distributed systems in Go."
    
    # Mock ollama response
    class MockMessage:
        content = '{"claims": [{"claim_category": "SKILL", "claim_key": "Go", "claim_value": "Go", "confidence_score": 0.9}]}'
        
    class MockResponse:
        message = MockMessage()
        
    def mock_chat(*args, **kwargs):
        return MockResponse()
        
    import ollama
    monkeypatch.setattr(ollama, "chat", mock_chat)
    
    facts = extract_inferences(text)
    assert len(facts) == 1
    assert facts[0]['claim_category'] == 'SKILL'
    assert facts[0]['claim_key'] == 'Go'
    assert facts[0]['confidence_score'] == 0.9
    assert facts[0]['source_type'] == 'AI_INFERENCE'
    assert facts[0]['extracted_by'] == 'OLLAMA_LLM_V1'

def test_extract_inferences_malformed_json(monkeypatch):
    text = "Text"
    class MockMessage:
        content = '{"claims": [broken json'
        
    class MockResponse:
        message = MockMessage()
        
    def mock_chat(*args, **kwargs):
        return MockResponse()
        
    import ollama
    monkeypatch.setattr(ollama, "chat", mock_chat)
    
    facts = extract_inferences(text)
    assert len(facts) == 0

def test_extract_inferences_exception(monkeypatch):
    text = "Text"
    
    def mock_chat(*args, **kwargs):
        raise ValueError("Connection failed")
        
    import ollama
    monkeypatch.setattr(ollama, "chat", mock_chat)
    
    facts = extract_inferences(text)
    assert len(facts) == 0
