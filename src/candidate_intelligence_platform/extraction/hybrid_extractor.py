import re
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from candidate_intelligence_platform.extraction.deterministic_ner import extract_facts, EMAIL_REGEX, PHONE_REGEX
from candidate_intelligence_platform.extraction.local_llm_fallback import extract_inferences

@dataclass
class ExtractionOutcome:
    first_name: str = ""
    last_name: str = ""
    primary_email: Optional[str] = None
    primary_phone: Optional[str] = None
    current_title: str = "Candidate"
    location: Optional[str] = None
    facts: List[Dict[str, Any]] = field(default_factory=list)
    confidence_score: float = 0.0
    used_ai_fallback: bool = False
    warnings: List[str] = field(default_factory=list)
    
    def get(self, key, default=None):
        return getattr(self, key, default)

    def __getitem__(self, key):
        return getattr(self, key)

TITLE_KEYWORDS = {
    "engineer", "developer", "manager", "lead", "architect", "analyst", 
    "specialist", "director", "administrator", "consultant", "designer", "scientist",
    "programmer", "officer", "executive", "coordinator", "technician", "cybersecurity",
    "security", "devops", "cloud", "qa"
}

TITLE_IGNORE_HEADINGS = {
    "summary", "professional summary", "executive summary", "career summary",
    "overview", "profile", "professional profile", "career profile", "profile summary",
    "personal profile", "personal summary", "summary of qualifications", "qualifications summary",
    "experience", "work experience", "professional experience", "employment history",
    "work history", "career history", "professional background", "employment background",
    "contact", "contact info", "contact information", "personal details", "personal information",
    "about", "about me", "objective", "career objective",
    "skills", "technical skills", "core competencies", "key skills",
    "technical expertise", "areas of expertise", "core qualifications",
    "education", "academic background", "certifications", "references",
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

def is_valid_name_format(parts: List[str]) -> bool:
    """Check if the sequence of words matches a plausible name format."""
    return 1 <= len(parts) <= 4 and all(re.match(r"^[A-Za-z\.\'\-]+$", p) for p in parts)

def validate_name_against_email(name: str, email: str | None) -> bool:
    """
    Validates a candidate name against their email address.
    Returns True if validated or if email is None/empty (neutral gate).
    """
    if not email:
        return True
    
    clean_name = re.sub(r'[^a-zA-Z\s]', '', name).lower().strip()
    if not clean_name:
        return False
        
    local_part = email.split('@')[0].lower()
    clean_local = re.sub(r'[^a-z]', '', local_part)
    
    name_parts = clean_name.split()
    
    # Strategy 1: All parts are in the email
    if all(part in clean_local for part in name_parts):
        return True
        
    # Strategy 2: Initial(s) + Surname
    if len(name_parts) >= 2:
        first_initial = name_parts[0][0]
        last_name = name_parts[-1]
        if f"{first_initial}{last_name}" in clean_local:
            return True
            
    # Add a fallback for fuzzy / partial typo or single name token
    for part in name_parts:
        if len(part) >= 3 and (part in clean_local or clean_local in part):
            return True
        if len(part) >= 4 and (part.startswith(clean_local[:4]) or clean_local.startswith(part[:4])):
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

def is_valid_title_text(text: str | None) -> bool:
    """Check if string is valid textual title, rejecting binary garbage/noise."""
    if not text:
        return False
    clean = text.strip()
    if not clean or clean.lower() == "candidate":
        return True
    letters = sum(1 for c in clean if c.isalpha())
    if letters < 3:
        return False
    if any(ord(c) < 32 and c not in ("\t", "\n", "\r") for c in clean):
        return False
    if "pk!" in clean.lower():
        return False
    symbols = sum(1 for c in clean if not c.isalnum() and not c.isspace() and c not in "-/&,.'\"()")
    return symbols <= letters


def normalize_title(text: str | None) -> str:
    """
    Format candidate job title cleanly in Title Case, filtering out binary artifacts.
    """
    if not text or not is_valid_title_text(text):
        return "Candidate"
    text = " ".join(text.strip().split())
    if not text or not is_valid_title_text(text):
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
    valid_name_found = False
    
    def process_name_str(n_str: str) -> Tuple[str, str]:
        parts = n_str.split()
        if len(parts) > 0:
            return normalize_name(parts[0]), normalize_name(" ".join(parts[1:])) if len(parts) > 1 else "Candidate"
        return "Uploaded", "Candidate"

    # Stage 1: Primary Discovery (Top Lines / NER)
    if name_from_ner and validate_name_against_email(name_from_ner, email):
        first_name, last_name = process_name_str(name_from_ner)
        valid_name_found = True
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
            if is_valid_name_format(parts):
                candidate_str = " ".join(parts)
                if validate_name_against_email(candidate_str, email):
                    first_name, last_name = process_name_str(candidate_str)
                    valid_name_found = True
                    break

    # Stage 2: Contact Block Positional Anchoring
    if not valid_name_found and lines:
        contact_idx = -1
        for i, line in enumerate(lines):
            clean_line = line.strip()
            if EMAIL_REGEX.search(clean_line) or PHONE_REGEX.search(clean_line):
                contact_idx = i
                break
                
        if contact_idx != -1:
            start_idx = max(0, contact_idx - 3)
            end_idx = min(len(lines), contact_idx + 2)
            for i in range(start_idx, end_idx):
                if i == contact_idx:
                    continue
                clean_line = lines[i].strip()
                if not clean_line or is_noise_header_line(clean_line):
                    continue
                parts = clean_line.split()
                if any(w.lower().rstrip(".,") in TITLE_KEYWORDS for w in parts) or clean_line.lower() in TITLE_IGNORE_HEADINGS:
                    continue
                if is_valid_name_format(parts):
                    candidate_str = " ".join(parts)
                    if validate_name_against_email(candidate_str, email):
                        first_name, last_name = process_name_str(candidate_str)
                        valid_name_found = True
                        break

    # Fallback: strict inference from email
    if not valid_name_found and email:
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
            
            current_first = profile["first_name"].lower()
            if cat == "PERSON" and val and (
                not current_first 
                or current_first in ("uploaded", "candidate", "profile", "summary", "curriculum", "resume", "objective", "experience", "education")
            ):
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
    
    current_first = profile["first_name"].lower()
    is_false_name = current_first in ("uploaded", "candidate", "profile", "summary", "curriculum", "resume", "objective", "experience", "education")
    
    missing_key_fields = (
        not profile["first_name"]
        or is_false_name
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
) -> ExtractionOutcome:
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

    return ExtractionOutcome(
        first_name=profile.get("first_name", ""),
        last_name=profile.get("last_name", ""),
        primary_email=profile.get("primary_email"),
        primary_phone=profile.get("primary_phone"),
        current_title=profile.get("current_title", "Candidate"),
        location=profile.get("location"),
        facts=facts,
        confidence_score=tier1_confidence if not used_ai else 0.85,
        used_ai_fallback=used_ai,
        warnings=warnings,
    )
