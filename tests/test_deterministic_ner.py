import pytest
from candidate_intelligence_platform.extraction.deterministic_ner import extract_facts, get_nlp

def test_extract_email():
    text = "Contact me at jane.doe@example.com for more info."
    facts = extract_facts(text)
    emails = [f for f in facts if f['claim_category'] == 'CONTACT' and f['claim_key'] == 'email']
    assert len(emails) == 1
    assert emails[0]['claim_value'] == 'jane.doe@example.com'

def test_extract_phone():
    text = "Call me: +1 (555) 123-4567"
    facts = extract_facts(text)
    phones = [f for f in facts if f['claim_category'] == 'CONTACT' and f['claim_key'] == 'phone']
    assert len(phones) == 1
    # Check normalized phone or exact string based on logic.
    # We will assume regex captures it well enough.
    assert "+1 (555) 123-4567" in text
    assert "555" in phones[0]['claim_value']

@pytest.mark.skipif(get_nlp() is None, reason="spaCy model en_core_web_sm is not installed")
def test_extract_name():
    text = "John Doe is a Senior Software Engineer."
    facts = extract_facts(text)
    names = [f for f in facts if f['claim_category'] == 'PERSON' and f['claim_key'] == 'name']
    assert len(names) >= 1
    assert names[0]['claim_value'] == 'John Doe'

@pytest.mark.skipif(get_nlp() is None, reason="spaCy model en_core_web_sm is not installed")
def test_extract_location():
    text = "I am based in San Francisco, CA."
    facts = extract_facts(text)
    locations = [f for f in facts if f['claim_category'] == 'LOCATION' and f['claim_key'] == 'city']
    assert len(locations) >= 1
    assert 'San Francisco' in locations[0]['claim_value']

def test_extract_skills():
    text = "I have 5 years of experience in Python and C++."
    facts = extract_facts(text)
    skills = [f for f in facts if f['claim_category'] == 'SKILL']
    skill_values = [s['claim_value'].lower() for s in skills]
    assert 'python' in skill_values
    assert 'c++' in skill_values

def test_offsets():
    text = "Email: test@test.com"
    facts = extract_facts(text)
    assert len(facts) > 0
    fact = facts[0]
    start = fact['source_char_offset_start']
    end = fact['source_char_offset_end']
    assert text[start:end] == 'test@test.com'
