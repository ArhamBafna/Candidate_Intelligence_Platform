import re
from typing import Dict, Any, List, Optional
from candidate_intelligence_platform.extraction.deterministic_ner import extract_facts, EMAIL_REGEX, PHONE_REGEX
from candidate_intelligence_platform.extraction.local_llm_fallback import extract_inferences

TITLE_KEYWORDS = {
    "engineer", "developer", "manager", "lead", "architect", "analyst", 
    "specialist", "director", "administrator", "consultant", "designer", "scientist",
    "programmer", "officer", "executive", "coordinator", "technician", "cybersecurity",
    "security", "devops", "cloud", "qa"
}

TITLE_IGNORE_HEADINGS = {
    "summary", "professional summary", "executive summary", "career summary",
    "overview", "profile", "professional profile", "career profile",
    "experience", "work experience", "professional experience", "employment history",
    "contact", "contact info", "contact information",
    "about", "about me", "objective", "career objective",
    "skills", "technical skills", "core competencies",
    "education", "academic background", "certifications",
    "resume", "curriculum vitae", "cv"
}

IGNORE_HEADER_PATTERNS = [
    re.compile(r'^page\s+\d+(\s+of\s+\d+)?$', re.IGNORECASE),
    re.compile(r'^\d+\s*/\s*\d+$'),
    re.compile(r'^[_\-=\*~]{3,}$'),
    re.compile(r'^(curriculum\s+vitae|resume|cv|confidential|profile|bio)$', re.IGNORECASE)
]

def is_noise_header_line(line: str) -> bool:
    line_clean = line.strip()
    if not line_clean:
        return True
    for pat in IGNORE_HEADER_PATTERNS:
        if pat.match(line_clean):
            return True
    return False

def normalize_name(text: str | None) -> str:
    """
    Format candidate name cleanly in Title Case while preserving special casing.
    Handles ALL CAPS (e.g. INZAMAM -> Inzamam), all lowercase, and mixed cases.
    """
    if not text:
        return ""
    text = " ".join(text.strip().split())
    if not text:
        return ""
    if text.lower() == "candidate" or text.lower() == "uploaded":
        return text.title()
    if text.isupper() or text.islower():
        return text.title()
    words = text.split()
    return " ".join(w.capitalize() if (w.isupper() or w.islower()) else w for w in words)

def normalize_title(text: str | None) -> str:
    """
    Format candidate job title cleanly in Title Case.
    """
    if not text:
        return "Candidate"
    text = " ".join(text.strip().split())
    if not text:
        return "Candidate"
    if text.isupper() or text.islower():
        return text.title()
    return text

def calculate_tier1_confidence(facts: List[Dict[str, Any]], parsed_profile: Dict[str, Any]) -> float:
    """
    Calculate confidence score (0.0 to 1.0) for Tier 1 deterministic extraction.
    
    Weights (100% total, excluding Email & Phone):
    - Name (50%): Valid candidate name (not default 'Uploaded Candidate').
    - Job Title (25%): Recognizable job title keyword.
    - Skills & Location (25%): Extracted explicit skills or location facts.
    """
    score = 0.0
    
    # 1. Name Check (50%)
    first_name = parsed_profile.get("first_name", "")
    last_name = parsed_profile.get("last_name", "")
    if first_name and first_name.lower() != "uploaded" and last_name and last_name.lower() != "candidate":
        score += 0.50
    elif first_name and first_name.lower() != "uploaded":
        score += 0.25

    # 2. Title Check (25%)
    title = (parsed_profile.get("current_title") or "").lower()
    if any(keyword in title for keyword in TITLE_KEYWORDS):
        score += 0.25

    # 3. Skills & Location (25%)
    has_skills_or_loc = any(
        f.get("claim_category") in ("SKILL", "LOCATION") for f in facts
    )
    if has_skills_or_loc:
        score += 0.25

    return min(1.0, round(score, 2))

def _extract_deterministic_profile(text: str, facts: List[Dict[str, Any]]) -> Dict[str, Any]:
    email = None
    phone = None
    name_from_ner = None
    location = None
    
    for f in facts:
        cat = f.get("claim_category")
        key = f.get("claim_key")
        val = f.get("claim_value")
        
        if cat == "CONTACT" and key == "email" and not email:
            email = val
        elif cat == "CONTACT" and key == "phone" and not phone:
            phone = val
        elif cat == "PERSON" and key == "name" and not name_from_ner:
            name_from_ner = val
        elif cat == "LOCATION" and not location:
            location = val

    lines = [line.strip() for line in text.split("\n") if line.strip()]
    first_name = "Uploaded"
    last_name = "Candidate"
    
    if name_from_ner:
        parts = name_from_ner.split()
        first_name = normalize_name(parts[0])
        last_name = normalize_name(" ".join(parts[1:])) if len(parts) > 1 else "Candidate"
    elif lines:
        for line in lines[:8]:
            clean_line = line.strip()
            if not clean_line or is_noise_header_line(clean_line):
                continue
            if EMAIL_REGEX.search(clean_line) or PHONE_REGEX.search(clean_line):
                continue
            if any(kw in clean_line.lower() for kw in ("http", "www", "github", "linkedin")):
                continue
            parts = clean_line.split()
            if any(w.lower().rstrip(".,") in TITLE_KEYWORDS for w in parts) or clean_line.lower() in TITLE_IGNORE_HEADINGS:
                continue
            if 1 <= len(parts) <= 4 and all(re.match(r"^[A-Za-z\.\'\-]+$", p) for p in parts):
                first_name = normalize_name(parts[0])
                last_name = normalize_name(" ".join(parts[1:])) if len(parts) > 1 else "Candidate"
                break

    if email:
        local_part = email.split("@")[0]
        if "." in local_part:
            email_parts = local_part.split(".")
            if len(email_parts) >= 2:
                if first_name.lower() in ("uploaded", "") or not first_name:
                    inferred_first = re.sub(r'\d+', '', email_parts[0])
                    if inferred_first and len(inferred_first) > 1:
                        first_name = normalize_name(inferred_first)
                if last_name.lower() in ("candidate", "") or not last_name:
                    inferred_last = re.sub(r'\d+', '', email_parts[1])
                    if inferred_last and len(inferred_last) > 1:
                        last_name = normalize_name(inferred_last)

    title = "Candidate"
    candidate_full_name = f"{first_name} {last_name}".strip().lower()
    for line in lines:
        clean_l = line.strip()
        if not clean_l or is_noise_header_line(clean_l):
            continue
        if EMAIL_REGEX.search(clean_l) or PHONE_REGEX.search(clean_l):
            continue
        lower_l = clean_l.lower()
        if lower_l in TITLE_IGNORE_HEADINGS:
            continue
        if lower_l == candidate_full_name or lower_l == first_name.lower():
            continue
        if any(kw in lower_l for kw in TITLE_KEYWORDS):
            words = clean_l.split()
            if len(words) > 7:
                match = re.search(r'^(.*?(?:professional|engineer|developer|analyst|specialist|architect|manager|lead|officer|consultant))', clean_l, re.IGNORECASE)
                if match:
                    title = normalize_title(match.group(1))
                else:
                    title = normalize_title(" ".join(words[:5]))
            else:
                title = normalize_title(clean_l[:100])
            break
        if title == "Candidate" and len(clean_l) <= 80 and not any(kw in lower_l for kw in ("http", "www", "github", "linkedin")):
            title = normalize_title(clean_l)

    return {
        "first_name": normalize_name(first_name[:50]),
        "last_name": normalize_name(last_name[:50]),
        "primary_email": email,
        "primary_phone": phone,
        "current_title": normalize_title(title),
        "location": normalize_title(location) if location else None,
    }

def _apply_llm_fallback(profile: Dict[str, Any], text: str, facts: List[Dict[str, Any]], model_name: Optional[str]) -> tuple[bool, List[str]]:
    warnings = []
    used_ai = False
    ai_claims = extract_inferences(text, model_name=model_name)
    if ai_claims:
        used_ai = True
        facts.extend(ai_claims)
        
        for claim in ai_claims:
            cat = claim.get("claim_category")
            val = claim.get("claim_value")
            key = (claim.get("claim_key") or "").lower()
            
            if cat == "PERSON" and val and (profile["first_name"] == "Uploaded" or not profile["first_name"] or profile["first_name"] == "Candidate"):
                parts = str(val).split()
                profile["first_name"] = normalize_name(parts[0][:50])
                profile["last_name"] = normalize_name(" ".join(parts[1:])[:50] if len(parts) > 1 else "Candidate")
            elif cat == "CONTACT" and key in ("email", "contact") and val and "@" in str(val) and not profile["primary_email"]:
                profile["primary_email"] = str(val).strip()
            elif cat == "CONTACT" and key in ("phone", "tel") and val and not profile["primary_phone"]:
                profile["primary_phone"] = str(val).strip()
            elif cat == "EMPLOYMENT" and val and key in ("title", "job_title", "position", "role") and (profile["current_title"] in ("Candidate", "Summary", "SUMMARY") or not profile["current_title"]):
                profile["current_title"] = normalize_title(str(val)[:100])
            elif cat == "EMPLOYMENT" and val and (profile["current_title"] in ("Candidate", "Summary", "SUMMARY") or not profile["current_title"]):
                if not re.search(r'\b(20\d\d|19\d\d|present)\b', str(val), re.IGNORECASE):
                    profile["current_title"] = normalize_title(str(val)[:100])
    else:
        warnings.append("LLM fallback attempted but LLM service/model unavailable; continued using rule-based profile extraction.")
        
    return used_ai, warnings

def assess_tier1(
    text: str, 
    facts: List[Dict[str, Any]],
    confidence_threshold: float = 0.70
) -> tuple[Dict[str, Any], float, bool]:
    """
    Assess Tier 1 extraction quality using precomputed facts.
    
    Returns:
        (profile, tier1_confidence, needs_ai): The deterministic profile, its confidence
        score, and whether AI fallback is needed.
    """
    profile = _extract_deterministic_profile(text, facts)
    tier1_confidence = calculate_tier1_confidence(facts, profile)
    
    has_skills_or_loc = any(
        f.get("claim_category") in ("SKILL", "LOCATION") for f in facts
    )
    
    missing_key_fields = (
        profile["first_name"] == "Uploaded" 
        or profile["current_title"] in ("Candidate", "Summary")
        or not has_skills_or_loc
    )
    
    needs_ai = tier1_confidence < confidence_threshold or missing_key_fields
    return profile, tier1_confidence, needs_ai


def extract_candidate_profile_hybrid(
    text: str, 
    confidence_threshold: float = 0.70, 
    model_name: Optional[str] = None,
    facts: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Extract candidate profile using Tier 1 deterministic parsing first.
    If Tier 1 confidence is below confidence_threshold (0.70) or if any of the key fields
    (Name, Job Title, or Skills/Location) are missing, trigger Tier 2 local AI LLM extraction.
    Applies Title Case normalization to candidate names and titles.
    
    Args:
        text: Raw resume text.
        confidence_threshold: Minimum confidence for Tier 1 extraction (default 0.70).
        model_name: Optional Ollama model name override.
        facts: Optional precomputed facts from extract_facts(). If provided, avoids
               re-running spaCy NER (significant speedup for multi-page resumes).
    """
    # Use precomputed facts if provided, otherwise extract fresh
    facts = facts if facts is not None else extract_facts(text)
    profile, tier1_confidence, needs_ai = assess_tier1(text, facts, confidence_threshold)
    used_ai = False

    warnings = []

    if needs_ai:
        used_ai, warnings = _apply_llm_fallback(profile, text, facts, model_name)

    # Final normalization guarantee
    profile["first_name"] = normalize_name(profile["first_name"])
    profile["last_name"] = normalize_name(profile["last_name"])
    profile["current_title"] = normalize_title(profile["current_title"])
    if profile.get("location"):
        profile["location"] = normalize_title(profile["location"])

    return {
        **profile,
        "confidence_score": tier1_confidence if not used_ai else 0.85,
        "used_ai_fallback": used_ai,
        "facts": facts,
        "warnings": warnings
    }
