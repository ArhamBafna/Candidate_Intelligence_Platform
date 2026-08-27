import re
import spacy

_nlp = None
_nlp_loaded = False

def get_nlp():
    global _nlp, _nlp_loaded
    if not _nlp_loaded:
        _nlp_loaded = True
        try:
            _nlp = spacy.load("en_core_web_sm")
        except BaseException:
            pass
    return _nlp

EMAIL_REGEX = re.compile(r"[\w\.-]+@[\w\.-]+\.\w+")
PHONE_REGEX = re.compile(r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}")

KNOWN_SKILLS = {
    "python", "c++", "java", "sql", "javascript", "react", "aws", "docker",
    "kubernetes", "typescript", "node.js", "go", "rust", "ruby", "php",
    "c#", ".net", "azure", "gcp", "terraform", "ansible", "linux", "git",
    "ci/cd", "machine learning", "data science", "angular", "vue.js",
    "html", "css", "postgresql", "mysql", "mongodb", "redis", "elasticsearch"
}

KNOWN_SKILLS_REGEXES = {}
for skill in KNOWN_SKILLS:
    escaped_skill = re.escape(skill)
    if skill == "c++":
        pattern = r'\b' + escaped_skill
    else:
        pattern = r'\b' + escaped_skill + r'\b'
    KNOWN_SKILLS_REGEXES[skill] = re.compile(pattern)

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
    for skill, pattern in KNOWN_SKILLS_REGEXES.items():
        for match in pattern.finditer(text_lower):
            facts.append({
                "source_type": "EXPLICIT_FACT",
                "claim_category": "SKILL",                "claim_key": skill,
                "claim_value": skill.title(),
                "source_char_offset_start": match.start(),
                "source_char_offset_end": match.end(),
                "extracted_by": "REGEX_PARSER",
                "confidence_score": 1.0
            })

    # 3. Spacy NER (Names, Locations) - truncate to header for speed
    # Names and locations are always in the first page; long resumes waste CPU
    nlp_instance = get_nlp()
    if nlp_instance is not None:
        # Truncate to first 5000 chars (covers ~2 pages of text)
        ner_text = text[:5000] if len(text) > 5000 else text
        doc = nlp_instance(ner_text)
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
