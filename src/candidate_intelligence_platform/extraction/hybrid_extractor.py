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
    
    Weights:
    - Name (35%): Valid candidate name (not default 'Uploaded Candidate').
    - Email (30%): Valid email matching regex.
    - Phone (15%): Valid phone number matching regex.
    - Title (10%): Recognizable job title keyword.
    - Skills/Location (10%): Extracted explicit skills or location facts.
    """
    score = 0.0
    
    # 1. Name Check (35%)
    first_name = parsed_profile.get("first_name", "")
    last_name = parsed_profile.get("last_name", "")
    if first_name and first_name.lower() != "uploaded" and last_name and last_name.lower() != "candidate":
        score += 0.35
    elif first_name and first_name.lower() != "uploaded":
        score += 0.20

    # 2. Email Check (30%)
    email = parsed_profile.get("primary_email")
    if email and EMAIL_REGEX.search(email):
        score += 0.30

    # 3. Phone Check (15%)
    phone = parsed_profile.get("primary_phone")
    if phone and PHONE_REGEX.search(phone):
        score += 0.15

    # 4. Title Check (10%)
    title = (parsed_profile.get("current_title") or "").lower()
    if any(keyword in title for keyword in TITLE_KEYWORDS):
        score += 0.10

    # 5. Skills & Location (10%)
    has_skills_or_loc = any(
        f.get("claim_category") in ("SKILL", "LOCATION") for f in facts
    )
    if has_skills_or_loc:
        score += 0.10

    return min(1.0, round(score, 2))

def extract_candidate_profile_hybrid(
    text: str, 
    confidence_threshold: float = 0.75, 
    model_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Extract candidate profile using Tier 1 deterministic parsing first.
    If Tier 1 confidence is below confidence_threshold (0.75) or missing key fields (Email, Job Title, or Name),
    trigger Tier 2 local AI LLM extraction.
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
    if len(lines) > 1:
        possible_title = lines[1]
        if not EMAIL_REGEX.search(possible_title) and not PHONE_REGEX.search(possible_title):
            title = possible_title[:100]

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

    # Check if key fields are missing or if Tier 1 confidence is below 0.75 threshold
    missing_key_fields = (
        profile["first_name"] == "Uploaded" 
        or not profile["primary_email"] 
        or profile["current_title"] == "Candidate"
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

    return {
        **profile,
        "confidence_score": tier1_confidence if not used_ai else 0.85,
        "used_ai_fallback": used_ai,
        "facts": facts
    }
