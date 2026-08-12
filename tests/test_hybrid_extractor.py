import pytest
from candidate_intelligence_platform.extraction.hybrid_extractor import (
    calculate_tier1_confidence,
    extract_candidate_profile_hybrid
)

def test_calculate_tier1_confidence_high():
    facts = [
        {"claim_category": "CONTACT", "claim_key": "email", "claim_value": "john.doe@example.com"},
        {"claim_category": "CONTACT", "claim_key": "phone", "claim_value": "555-123-4567"},
        {"claim_category": "PERSON", "claim_key": "name", "claim_value": "John Doe"},
        {"claim_category": "SKILL", "claim_key": "python", "claim_value": "Python"}
    ]
    parsed_profile = {
        "first_name": "John",
        "last_name": "Doe",
        "primary_email": "john.doe@example.com",
        "primary_phone": "555-123-4567",
        "current_title": "Senior Software Engineer"
    }
    score = calculate_tier1_confidence(facts, parsed_profile)
    assert score >= 0.70

def test_calculate_tier1_confidence_very_low():
    facts = []
    parsed_profile = {
        "first_name": "Uploaded",
        "last_name": "Candidate",
        "primary_email": None,
        "primary_phone": None,
        "current_title": "Candidate"
    }
    score = calculate_tier1_confidence(facts, parsed_profile)
    assert score < 0.40

def test_extract_candidate_profile_hybrid_deterministic():
    text = """
    John Doe
    john.doe@example.com | (555) 123-4567
    Senior Software Engineer
    San Francisco, CA
    Skills: Python, SQL, Docker
    """
    res = extract_candidate_profile_hybrid(text, confidence_threshold=0.70)
    assert res["first_name"] == "John"
    assert res["last_name"] == "Doe"
    assert res["primary_email"] == "john.doe@example.com"
    assert res["used_ai_fallback"] is False
    assert res["confidence_score"] >= 0.70

def test_extract_candidate_profile_hybrid_ai_fallback(monkeypatch):
    # Missing email triggers AI fallback even if name is present
    text = "John Doe\nSenior Software Engineer\nSkills: Python"
    
    class MockMessage:
        content = '{"claims": [{"claim_category": "PERSON", "claim_key": "name", "claim_value": "John Doe"}, {"claim_category": "CONTACT", "claim_key": "email", "claim_value": "john.doe@inferred.com"}]}'
        
    class MockResponse:
        message = MockMessage()
        
    def mock_chat(*args, **kwargs):
        return MockResponse()
        
    import ollama
    monkeypatch.setattr(ollama, "chat", mock_chat)
    
    res = extract_candidate_profile_hybrid(text)
    assert res["used_ai_fallback"] is True
    assert res["primary_email"] == "john.doe@inferred.com"
