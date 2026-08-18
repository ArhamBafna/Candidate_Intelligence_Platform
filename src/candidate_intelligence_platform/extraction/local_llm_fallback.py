import json
import ollama
import structlog
from config.settings import Settings

logger = structlog.get_logger(__name__)

VALID_CATEGORIES = {"PERSON", "CONTACT", "EMPLOYMENT", "SKILL", "EDUCATION", "LOCATION"}

def extract_inferences(text: str, model_name: str | None = None) -> list[dict]:
    """
    Extract AI inferences from text using a local LLM via Ollama.
    Defaults to configured Settings model (llama3.2).
    Includes validation, anomaly logging, and self-healing for LLM schema deviations.
    """
    selected_model = model_name or Settings().llm_model
    prompt = f"""
You are an expert fact-extraction engine for resumes. Extract all candidate facts into structured JSON.

Rules:
- Output category strictly as one of: PERSON, CONTACT, EMPLOYMENT, SKILL, EDUCATION, LOCATION.
- claim_key must be the descriptor/type (e.g., 'name', 'email', 'phone', 'title', 'company', 'skill', 'degree', 'institution', 'location').
- claim_value must contain the actual extracted text snippet (NEVER null or empty).
- confidence_score must be a float between 0.80 and 1.00.

Return ONLY valid JSON matching this schema:
{{
  "claims": [
    {{
      "claim_category": "PERSON",
      "claim_key": "name",
      "claim_value": "Jane Doe",
      "confidence_score": 0.95
    }},
    {{
      "claim_category": "CONTACT",
      "claim_key": "email",
      "claim_value": "jane@example.com",
      "confidence_score": 0.98
    }},
    {{
      "claim_category": "EMPLOYMENT",
      "claim_key": "title",
      "claim_value": "Senior Software Engineer",
      "confidence_score": 0.95
    }},
    {{
      "claim_category": "SKILL",
      "claim_key": "skill",
      "claim_value": "Python",
      "confidence_score": 0.92
    }},
    {{
      "claim_category": "EDUCATION",
      "claim_key": "degree",
      "claim_value": "B.S. in Computer Science",
      "confidence_score": 0.90
    }}
  ]
}}

Text:
{text}
"""
    
    try:
        response = ollama.chat(
            model=selected_model,
            messages=[
                {
                    'role': 'user',
                    'content': prompt
                }
            ],
            format='json'
        )
        
        content = response.message.content
        try:
            data = json.loads(content)
        except json.JSONDecodeError as jde:
            logger.warning("ai_llm_json_decode_failed", model=selected_model, error=str(jde), raw_content=content)
            return []
            
        if not isinstance(data, dict) or "claims" not in data or not isinstance(data["claims"], list):
            logger.warning("ai_llm_malformed_response_schema", model=selected_model, raw_data=data)
            return []
            
        claims = data.get("claims", [])
        facts = []
        
        for idx, claim in enumerate(claims):
            if not isinstance(claim, dict):
                logger.warning("ai_llm_invalid_claim_item", index=idx, raw_claim=claim)
                continue

            raw_cat = str(claim.get("claim_category") or "").strip().upper()
            raw_key = claim.get("claim_key")
            raw_val = claim.get("claim_value")
            raw_score = claim.get("confidence_score")

            # 1. Check and repair category
            if raw_cat not in VALID_CATEGORIES:
                logger.warning(
                    "ai_llm_unknown_claim_category",
                    original_category=claim.get("claim_category"),
                    normalized_category=raw_cat or "SKILL"
                )
                raw_cat = raw_cat if raw_cat in VALID_CATEGORIES else "SKILL"

            # 2. Check and repair claim_value / claim_key inversion (where claim_value was null)
            repaired_key = str(raw_key).strip() if raw_key is not None else ""
            repaired_val = str(raw_val).strip() if raw_val is not None else ""

            if not repaired_val and repaired_key:
                logger.warning(
                    "ai_llm_claim_value_missing_repaired",
                    issue="claim_value is null or empty, entity was placed in claim_key",
                    original_key=raw_key,
                    action="moved_key_to_value"
                )
                repaired_val = repaired_key
                # Provide a generic key for the category
                default_keys = {
                    "SKILL": "skill",
                    "EMPLOYMENT": "title",
                    "EDUCATION": "degree",
                    "PERSON": "name",
                    "CONTACT": "contact",
                    "LOCATION": "location"
                }
                repaired_key = default_keys.get(raw_cat, "extracted_fact")
            elif not repaired_val and not repaired_key:
                logger.warning("ai_llm_empty_claim_skipped", index=idx, claim=claim)
                continue

            # 3. Check and repair confidence score
            try:
                score = float(raw_score)
                if score <= 0.0 or score > 1.0:
                    logger.warning(
                        "ai_llm_invalid_confidence_score",
                        original_score=raw_score,
                        action="defaulted_to_0.90"
                    )
                    score = 0.90
            except (ValueError, TypeError):
                logger.warning(
                    "ai_llm_non_numeric_confidence_score",
                    original_score=raw_score,
                    action="defaulted_to_0.90"
                )
                score = 0.90

            facts.append({
                "source_type": "AI_INFERENCE",
                "claim_category": raw_cat,
                "claim_key": repaired_key,
                "claim_value": repaired_val,
                "confidence_score": round(score, 2),
                "source_char_offset_start": None,
                "source_char_offset_end": None,
                "extracted_by": "OLLAMA_LLM_V1"
            })
            
        return facts
    except Exception as e:
        logger.warning("ai_llm_extraction_failed", model=selected_model, error=str(e), action="skipping_ai_extraction")
        return []
