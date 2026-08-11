import re
import spacy

try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    import spacy.cli
    spacy.cli.download("en_core_web_sm")
    nlp = spacy.load("en_core_web_sm")

EMAIL_REGEX = re.compile(r"[\w\.-]+@[\w\.-]+\.\w+")
PHONE_REGEX = re.compile(r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}")

KNOWN_SKILLS = {"python", "c++", "java", "sql", "javascript", "react", "aws", "docker"}

def extract_facts(text: str) -> list[dict]:
    """
    Extract deterministic facts (emails, phones, locations, names, skills) from text.
    """
    facts = []
    
    # 1. Regex Extractions
    for match in EMAIL_REGEX.finditer(text):
        facts.append({
            "source_type": "EXPLICIT_FACT",
            "claim_category": "CONTACT",
            "claim_key": "email",
            "claim_value": match.group(0),
            "source_char_offset_start": match.start(),
            "source_char_offset_end": match.end(),
            "extracted_by": "REGEX_PARSER",
            "confidence_score": 1.0
        })

    for match in PHONE_REGEX.finditer(text):
        facts.append({
            "source_type": "EXPLICIT_FACT",
            "claim_category": "CONTACT",
            "claim_key": "phone",
            "claim_value": match.group(0),
            "source_char_offset_start": match.start(),
            "source_char_offset_end": match.end(),
            "extracted_by": "REGEX_PARSER",
            "confidence_score": 1.0
        })
        
    # 2. Skill Extraction (Dictionary based)
    text_lower = text.lower()
    for skill in KNOWN_SKILLS:
        # Avoid partial word matches by using word boundaries
        # Handle cases like c++ which contain regex special characters
        escaped_skill = re.escape(skill)
        # We need \b for word boundaries, but C++ doesn't have a word boundary after ++
        if skill == "c++":
            pattern = r'\b' + escaped_skill
        else:
            pattern = r'\b' + escaped_skill + r'\b'
            
        for match in re.finditer(pattern, text_lower):
            facts.append({
                "source_type": "EXPLICIT_FACT",
                "claim_category": "SKILL",
                "claim_key": skill,
                "claim_value": skill.title(),
                "source_char_offset_start": match.start(),
                "source_char_offset_end": match.end(),
                "extracted_by": "REGEX_PARSER",
                "confidence_score": 1.0
            })

    # 3. Spacy NER (Names, Locations)
    doc = nlp(text)
    for ent in doc.ents:
        if ent.label_ == "PERSON":
            facts.append({
                "source_type": "EXPLICIT_FACT",
                "claim_category": "PERSON",
                "claim_key": "name",
                "claim_value": ent.text,
                "source_char_offset_start": ent.start_char,
                "source_char_offset_end": ent.end_char,
                "extracted_by": "SPACY_NER",
                "confidence_score": 1.0
            })
        elif ent.label_ in ("GPE", "LOC"):
            facts.append({
                "source_type": "EXPLICIT_FACT",
                "claim_category": "LOCATION",
                "claim_key": "city",
                "claim_value": ent.text,
                "source_char_offset_start": ent.start_char,
                "source_char_offset_end": ent.end_char,
                "extracted_by": "SPACY_NER",
                "confidence_score": 1.0
            })
            
    return facts
