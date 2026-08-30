import pytest
from candidate_intelligence_platform.extraction.hybrid_extractor import (
    calculate_tier1_confidence,
    extract_candidate_profile_hybrid,
    validate_name_against_email
)

def test_calculate_tier1_confidence_high():
    facts = [
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
    assert score == 1.0  # Name (0.50) + Title (0.25) + Skills (0.25) = 1.0

def test_calculate_tier1_confidence_no_email_phone_bonus():
    # Email & phone present, but no title or skills -> score is only for Name (0.50)
    facts = [
        {"claim_category": "CONTACT", "claim_key": "email", "claim_value": "john.doe@example.com"},
        {"claim_category": "CONTACT", "claim_key": "phone", "claim_value": "555-123-4567"}
    ]
    parsed_profile = {
        "first_name": "John",
        "last_name": "Doe",
        "primary_email": "john.doe@example.com",
        "primary_phone": "555-123-4567",
        "current_title": "Candidate"
    }
    score = calculate_tier1_confidence(facts, parsed_profile)
    assert score == 0.50

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
    assert score == 0.0

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
    # Missing skills/location triggers AI fallback even if name & title are present
    text = "John Doe\nSenior Software Engineer"
    
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

def test_extract_candidate_profile_hybrid_ai_fallback_failed_warning(monkeypatch):
    # Text missing skills triggers fallback, but ollama returns []
    text = "Jane Smith\nSoftware Engineer"
    
    def mock_extract_inferences(*args, **kwargs):
        return []
        
    monkeypatch.setattr("candidate_intelligence_platform.extraction.hybrid_extractor.extract_inferences", mock_extract_inferences)
    
    res = extract_candidate_profile_hybrid(text)
    assert res["used_ai_fallback"] is False
    assert hasattr(res, "warnings") and len(res.warnings) > 0
    assert any("LLM fallback attempted" in w for w in res["warnings"])

def test_extract_candidate_profile_with_page_header_noise():
    text = """
    Page 1 of 2
    SRINIVAS PEDDI
    Alpharetta, GA | (404) 992-1973 | srinipe28@gmail.com
    ____________________________________________________
    PROFESSIONAL SUMMARY
    Cybersecurity professional with extensive experience partnering with engineering teams.
    Skills: Python, SQL, Docker, AWS
    """
    res = extract_candidate_profile_hybrid(text, confidence_threshold=0.70)
    assert res["first_name"] == "Srinivas"
    assert res["last_name"] == "Peddi"
    assert res["primary_email"] == "srinipe28@gmail.com"
    assert res["primary_phone"] == "(404) 992-1973"
    assert "Cybersecurity" in res["current_title"]
    assert res["used_ai_fallback"] is False
    assert res["confidence_score"] >= 0.70



def test_validate_name_against_email():
    # True positives
    assert validate_name_against_email("John Doe", "john.doe@example.com") is True
    assert validate_name_against_email("John Doe", "johndoe@example.com") is True
    assert validate_name_against_email("John Smith", "jsmith@example.com") is True
    assert validate_name_against_email("John Smith", "j.smith@example.com") is True
    # Fuzzy / typos
    assert validate_name_against_email("Jonathan Doe", "jon.doe@example.com") is True
    # No email
    assert validate_name_against_email("Jane Smith", None) is True
    assert validate_name_against_email("Jane Smith", "") is True
    # False positives
    assert validate_name_against_email("Executive Summary", "john.doe@example.com") is False
    assert validate_name_against_email("Profile Overview", "jsmith@example.com") is False
    assert validate_name_against_email("John", "alex.smith@example.com") is False
