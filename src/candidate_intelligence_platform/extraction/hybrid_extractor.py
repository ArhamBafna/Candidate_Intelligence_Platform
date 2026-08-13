import re
from typing import Dict, Any, List, Optional
from candidate_intelligence_platform.extraction.deterministic_ner import extract_facts, EMAIL_REGEX, PHONE_REGEX
from candidate_intelligence_platform.extraction.local_llm_fallback import extract_inferences

TITLE_KEYWORDS = {
    "engineer", "developer", "manager", "lead", "architect", "analyst", 
    "specialist", "director", "administrator", "consultant", "designer", "scientist"
}

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

def extract_candidate_profile_hybrid(
    text: str, 
    confidence_threshold: float = 0.70, 
    model_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Extract candidate profile using Tier 1 deterministic parsing first.
    If Tier 1 confidence is below confidence_threshold (0.70) or if any of the key fields
    (Name, Job Title, or Skills/Location) are missing, trigger Tier 2 local AI LLM extraction.
    """
    facts = extract_facts(text)
    
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
        first_name = parts[0]
        last_name = " ".join(parts[1:]) if len(parts) > 1 else "Candidate"
    elif lines:
        header_line = lines[0]
        if not EMAIL_REGEX.search(header_line) and not PHONE_REGEX.search(header_line):
            parts = header_line.split()
            if 1 <= len(parts) <= 3:
                first_name = parts[0]
                last_name = parts[1] if len(parts) > 1 else "Candidate"

    title = "Candidate"
    for line in lines[1:]:
        if not EMAIL_REGEX.search(line) and not PHONE_REGEX.search(line):
            title = line[:100]
            break

    profile = {
        "first_name": first_name[:50],
        "last_name": last_name[:50],
        "primary_email": email,
        "primary_phone": phone,
        "current_title": title,
        "location": location,
    }

    tier1_confidence = calculate_tier1_confidence(facts, profile)
    used_ai = False

    warnings = []

    has_skills_or_loc = any(
        f.get("claim_category") in ("SKILL", "LOCATION") for f in facts
    )

    # Check if Tier 1 confidence is below threshold or if any key field (Name, Job Title, Skills/Loc) is missing
    missing_key_fields = (
        profile["first_name"] == "Uploaded" 
        or profile["current_title"] == "Candidate"
        or not has_skills_or_loc
    )

    if tier1_confidence < confidence_threshold or missing_key_fields:
        ai_claims = extract_inferences(text, model_name=model_name)
        if ai_claims:
            used_ai = True
            facts.extend(ai_claims)
            
            for claim in ai_claims:
                cat = claim.get("claim_category")
                val = claim.get("claim_value")
                key = claim.get("claim_key")
                
                if cat == "PERSON" and val and (profile["first_name"] == "Uploaded" or not profile["first_name"]):
                    parts = str(val).split()
                    profile["first_name"] = parts[0][:50]
                    profile["last_name"] = parts[1][:50] if len(parts) > 1 else "Candidate"
                elif cat == "CONTACT" and key == "email" and val and not profile["primary_email"]:
                    profile["primary_email"] = str(val)
                elif cat == "EMPLOYMENT" and val and (profile["current_title"] == "Candidate" or not profile["current_title"]):
                    profile["current_title"] = str(val)[:100]
        else:
            warnings.append("LLM fallback attempted but LLM service/model unavailable; continued using rule-based profile extraction.")

    return {
        **profile,
        "confidence_score": tier1_confidence if not used_ai else 0.85,
        "used_ai_fallback": used_ai,
        "facts": facts,
        "warnings": warnings
    }

