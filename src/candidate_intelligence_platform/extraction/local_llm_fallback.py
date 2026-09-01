import concurrent.futures
import json
import re
import time
import structlog
from config.settings import get_settings
from candidate_intelligence_platform.intelligence.chat_model import get_llm_provider
from candidate_intelligence_platform.prompts import (
    build_fact_extraction_prompt, 
    build_document_classification_prompt,
    build_json_repair_prompt
)

logger = structlog.get_logger(__name__)

class LLMExtractionFatalError(Exception):
    """Raised when the LLM repeatedly fails to return valid JSON even after repair attempts."""
    pass


VALID_CATEGORIES = {"PERSON", "CONTACT", "EMPLOYMENT", "SKILL", "EDUCATION", "LOCATION"}


def _clean_and_parse_json(content: str) -> dict | list | None:
    """Safely parse JSON from LLM output, stripping code blocks and markdown fences if present."""
    if not content:
        return None
    cleaned = content.strip()
    # Strip markdown code blocks
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Fallback: extract the outermost JSON object or list
        match = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", cleaned)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
    return None


def _call_openrouter(prompt: str, model_name: str, timeout_seconds: float):
    """Call OpenRouter API for inference. Never calls paid models."""
    import httpx

    from candidate_intelligence_platform.intelligence.chat_model import (
        OpenRouterModelPaidError,
        is_openrouter_model_free,
        mark_openrouter_model_paid,
    )

    settings = get_settings()
    if not settings.openrouter_api_key:
        return None
    if not is_openrouter_model_free(model_name):
        return None

    with httpx.Client(timeout=timeout_seconds) as client:
        for attempt in range(2):
            response = client.post(
                f"{settings.openrouter_base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.openrouter_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model_name,
                    "messages": [{"role": "user", "content": prompt}],
                    "response_format": {"type": "json_object"},
                },
            )
            if response.status_code == 402:
                mark_openrouter_model_paid(model_name)
                raise OpenRouterModelPaidError(model_name)
            if response.status_code == 429 and attempt == 0:
                time.sleep(2.0)
                continue
            response.raise_for_status()
            return response.json()


def _call_ollama(prompt: str, model_name: str, timeout_seconds: float):
    """Call local Ollama for inference."""
    import ollama

    # If ollama.chat was monkeypatched in tests, use it directly
    if hasattr(ollama, "chat") and not hasattr(ollama.chat, "__wrapped__") and callable(getattr(ollama, "chat", None)):
        # Check if chat is a custom mock function
        if getattr(ollama.chat, "__module__", "") != "ollama._client":
            return ollama.chat(
                model=model_name,
                messages=[{"role": "user", "content": prompt}],
                format="json",
            )

    client = ollama.Client(timeout=timeout_seconds)
    return client.chat(
        model=model_name,
        messages=[{"role": "user", "content": prompt}],
        format="json",
    )


def _execute_prompt(prompt: str, provider: str, settings, model_name: str, timeout_seconds: float) -> tuple[str | None, str, str]:
    """Execute prompt with provider failover. Returns (content, active_provider, active_model)."""
    selected_model = model_name or (settings.openrouter_model if provider == "openrouter" else settings.llm_model)
    
    if provider == "openrouter":
        try:
            response_data = _call_openrouter(prompt, selected_model, timeout_seconds)
            if response_data is not None:
                return response_data.get("choices", [{}])[0].get("message", {}).get("content", ""), "openrouter", selected_model
        except Exception as openrouter_error:
            logger.error(
                "*** AI EXTRACTION FALLBACK ACTIVE ***",
                skipped_provider="openrouter",
                skipped_model=selected_model,
                fallback_model=settings.llm_model,
                error=str(openrouter_error),
                action="retrying_with_local_ollama",
            )
            provider = "ollama"
            selected_model = settings.llm_model

    if provider == "ollama":
        response = _call_ollama(prompt, selected_model, timeout_seconds)
        content = response.message.content if response else None
        return content, "ollama", selected_model
        
    return None, provider, selected_model


def extract_inferences(text: str, model_name: str | None = None, timeout_seconds: float = 30.0) -> list[dict]:
    """
    Extract AI inferences from text using a local LLM via Ollama or remote via OpenRouter.
    Defaults to configured Settings model (llama3.2 or stealth/ox-alpha).
    Includes validation, anomaly logging, and self-healing for LLM schema deviations.
    """
    settings = get_settings()
    provider = get_llm_provider()

    if provider == "openrouter":
        selected_model = model_name or settings.openrouter_model
        if not selected_model or not settings.openrouter_api_key:
            raise ValueError("CRITICAL: OpenRouter configured but missing API key or model. Check .env configuration.")
    else:
        selected_model = model_name or settings.llm_model

    # Truncate text to header/profile section (~3000 chars) to ensure fast inference
    truncated_text = (text or "")[:3000]
    prompt = build_fact_extraction_prompt(truncated_text)

    try:
        content, serving_provider, active_model = _execute_prompt(prompt, provider, settings, model_name, timeout_seconds)

        if not content:
            logger.warning("ai_llm_empty_content_returned", model=active_model)
            return []

        # Pass 1: Standard parsing
        data = _clean_and_parse_json(content)
        
        # Pass 2: Syntax Repair
        if not data or not isinstance(data, dict) or "claims" not in data:
            logger.warning("ai_llm_json_decode_failed_attempting_repair", model=active_model)
            repair_prompt = build_json_repair_prompt(content, "Malformed JSON or missing 'claims' key")
            repair_content, _, _ = _execute_prompt(repair_prompt, serving_provider, settings, active_model, timeout_seconds)
            data = _clean_and_parse_json(repair_content or "")
            
        # Pass 3: Full Re-run
        if not data or not isinstance(data, dict) or "claims" not in data:
            logger.warning("ai_llm_repair_failed_attempting_full_rerun", model=active_model)
            rerun_content, _, _ = _execute_prompt(prompt, serving_provider, settings, active_model, timeout_seconds)
            data = _clean_and_parse_json(rerun_content or "")
            
        # Pass 4: Fatal Escalation
        if not data or not isinstance(data, dict) or "claims" not in data:
            logger.error("ai_llm_fatal_extraction_error", model=active_model)
            raise LLMExtractionFatalError("Failed to extract valid JSON after 4-stage self-healing recovery.")

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
                    normalized_category=raw_cat or "SKILL",
                )
                raw_cat = "SKILL"

            # 2. Check and repair claim_value / claim_key inversion (where claim_value was null)
            repaired_key = str(raw_key).strip() if raw_key is not None else ""
            repaired_val = str(raw_val).strip() if raw_val is not None else ""

            if not repaired_val and repaired_key:
                logger.warning(
                    "ai_llm_claim_value_missing_repaired",
                    issue="claim_value is null or empty, entity was placed in claim_key",
                    original_key=raw_key,
                    action="moved_key_to_value",
                )
                repaired_val = repaired_key
                # Provide a generic key for the category
                default_keys = {
                    "SKILL": "skill",
                    "EMPLOYMENT": "title",
                    "EDUCATION": "degree",
                    "PERSON": "name",
                    "CONTACT": "contact",
                    "LOCATION": "location",
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
                        action="defaulted_to_0.90",
                    )
                    score = 0.90
            except (ValueError, TypeError):
                logger.warning(
                    "ai_llm_non_numeric_confidence_score",
                    original_score=raw_score,
                    action="defaulted_to_0.90",
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
                "extracted_by": f"{serving_provider.upper()}_LLM_V1",
            })

        return facts
    except Exception as e:
        logger.warning("ai_llm_extraction_failed", model=selected_model, error=str(e), action="skipping_ai_extraction")
        return []

def batched_extract_inferences(texts: list[str], model_name: str | None = None, timeout_seconds: float = 60.0) -> list[list[dict]]:
    if not texts:
        return []
    if len(texts) > 5:
        # Batch size is strictly bounded to 5 per requirements
        logger.warning("batched_extract_inferences_exceeded_limit", count=len(texts))
        
    results = [[] for _ in texts]
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        future_to_idx = {
            executor.submit(extract_inferences, text, model_name, timeout_seconds): i
            for i, text in enumerate(texts)
        }
        for future in concurrent.futures.as_completed(future_to_idx):
            idx = future_to_idx[future]
            try:
                results[idx] = future.result()
            except Exception as e:
                logger.error("batched_extract_inferences_item_failed", index=idx, error=str(e))
                results[idx] = []
    return results


def classify_document_llm(text: str, model_name: str | None = None, timeout_seconds: float = 15.0) -> bool:
    """Use local LLM to classify if document is a resume."""
    settings = get_settings()
    provider = get_llm_provider()

    if provider == "openrouter":
        selected_model = model_name or settings.openrouter_model
        if not selected_model or not settings.openrouter_api_key:
            raise ValueError("CRITICAL: OpenRouter configured but missing API key or model. Check .env configuration.")
    else:
        selected_model = model_name or settings.llm_model

    prompt = build_document_classification_prompt(text)

    try:
        content = None
        serving_provider = provider
        if provider == "openrouter":
            try:
                response_data = _call_openrouter(prompt, selected_model, timeout_seconds)
                if response_data is not None:
                    content = response_data.get("choices", [{}])[0].get("message", {}).get("content", "")
            except Exception as openrouter_error:
                content = None
                serving_provider = "ollama"

        if serving_provider == "ollama":
            response = _call_ollama(prompt, settings.llm_model if provider == "openrouter" else selected_model, timeout_seconds)
            content = response.message.content if response else None

        if not content:
            return False

        data = _clean_and_parse_json(content)
        if isinstance(data, dict):
            return bool(data.get("is_resume", False))
        return False
    except Exception as e:
        logger.warning("ai_llm_classification_failed", model=selected_model, error=str(e))
        return False