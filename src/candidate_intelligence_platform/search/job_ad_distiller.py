"""Paste-a-job-ad mode: distill a full job advertisement into a structured search recipe.

The recruiter may paste an entire job ad into the single search box. Before
searching, the ad is distilled locally (configured chat model first, simple
non-AI extraction second, raw passthrough last) into:

  - job title            -> strict title equality filter
  - must-have skills     -> keyword search terms
  - years of experience  -> minimum-yoe numeric filter
  - location             -> city equality filter
  - short summary        -> meaning-based (embedding) search input that fits
                             the embedding model read limit

Supports both local Ollama and remote OpenRouter providers.
"""
from __future__ import annotations

import concurrent.futures
import json
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import structlog

from candidate_intelligence_platform.intelligence.chat_model import (
    get_llm_provider,
    resolve_chat_model,
)
from config.settings import Settings

logger = structlog.get_logger(__name__)

JOB_AD_MIN_CHARS = 350

SUMMARY_MAX_CHARS = 1200

_YOE_PATTERN = re.compile(r"(\d+(?:\.\d+)?)\s*\+?\s*(?:to\s*(\d+(?:\.\d+)?)\s*)?(?:years?|yrs?)\s+(?:of\s+)?(?:relevant\s+|professional\s+|work\s+)?experience", re.IGNORECASE)

_TITLE_HINTS = (
    "engineer", "developer", "manager", "designer", "analyst", "scientist",
    "architect", "lead", "consultant", "specialist", "administrator",
    "technician", "recruiter", "director", "intern",
)

# Sentence filler words that must never leak into an extracted title phrase
# (PR #25 review: "We are hiring a Senior Data Engineer to join our team"
# must yield "Senior Data Engineer", not the whole sentence).
_TITLE_PHRASE_STOPS = frozenset({
    "we", "our", "us", "you", "your", "they", "their",
    "are", "is", "was", "were", "be", "been",
    "a", "an", "the", "and", "or", "for", "with", "to", "at", "on", "in", "of", "as", "by",
    "hiring", "seeking", "join", "joining", "team", "role", "position", "job",
})

_STOPWORDS = frozenset("""
a an and are as at be by for from has have how in is it its of on or our that
the this to will with you your we us they their them who whom what when where
why all any both each few more most other some such no nor not only own same
so than too very can just should now about into over under again further once
here there out up down off above below between during before after while
because until against does doing done been being was were am i me my he she
his her him if then do also may might must shall would could need wants want
looking look join team role position job work working candidate candidates
ability strong plus etc via per across within using use used well good great
years year experience experienced responsibilities requirements required
require qualifications preferred plus bonus company inc llc ltd full time
part remote hybrid onsite office new york city san francisco
""".split())


@dataclass
class JobAdRecipe:
    """Structured understanding of a pasted job ad."""
    title: Optional[str]
    skills: List[str]
    min_yoe: Optional[float]
    location: Optional[str]
    summary: str
    source: str
    warnings: List[str] = field(default_factory=list)

    def to_metadata(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "skills": self.skills,
            "min_yoe": self.min_yoe,
            "location": self.location,
            "summary": self.summary,
            "source": self.source,
            "warnings": list(self.warnings),
        }


def looks_like_job_ad(text: str) -> bool:
    """Heuristic: a long multi-line paste is treated as a full job ad."""
    stripped = (text or "").strip()
    if len(stripped) < JOB_AD_MIN_CHARS:
        return False
    return True


def _truncate_summary(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", (text or "")).strip()
    return cleaned[:SUMMARY_MAX_CHARS]


def _build_summary(title: Optional[str], skills: List[str], min_yoe: Optional[float], ad_text: str) -> str:
    bits: List[str] = []
    if title:
        bits.append(f"Role: {title}")
    if skills:
        bits.append("Skills: " + ", ".join(skills))
    if min_yoe is not None:
        formatted = f"{min_yoe:g}"
        bits.append(f"Experience: {formatted}+ years")
    lead = ". ".join(bits)
    tail = _truncate_summary(ad_text)[:600]
    combined = f"{lead}. {tail}" if lead else tail
    return _truncate_summary(combined)


def _coerce_recipe(data: Any, ad_text: str, source: str, warnings: List[str]) -> Optional[JobAdRecipe]:
    """Validate a raw distillation payload into a JobAdRecipe."""
    if not isinstance(data, dict):
        return None

    title_raw = data.get("title")
    title = str(title_raw).strip() if title_raw else None
    if title == "":
        title = None

    skills_raw = data.get("skills") or []
    if isinstance(skills_raw, str):
        skills_raw = [part.strip() for part in skills_raw.split(",")]
    if not isinstance(skills_raw, list):
        skills_raw = []
    skills = []
    for item in skills_raw:
        skill = str(item).strip()
        if skill and skill.lower() not in {s.lower() for s in skills}:
            skills.append(skill)

    min_yoe: Optional[float] = None
    yoe_raw = data.get("min_yoe", data.get("years_of_experience"))
    if yoe_raw is not None:
        try:
            min_yoe = float(yoe_raw)
        except (TypeError, ValueError):
            min_yoe = None

    location_raw = data.get("location")
    location = str(location_raw).strip() if location_raw else None
    if location == "":
        location = None

    usable = bool(title) or bool(skills) or min_yoe is not None
    if not usable:
        return None

    return JobAdRecipe(
        title=title,
        skills=skills,
        min_yoe=min_yoe,
        location=location,
        summary=_build_summary(title, skills, min_yoe, ad_text),
        source=source,
        warnings=warnings,
    )


_DISTILL_PROMPT = """
You are a precise job-ad parser for a recruiting search engine.
Extract the structured requirements from the job advertisement below.

Return ONLY valid JSON with exactly these keys:
{{
  "title": "<job title or null>",
  "skills": ["must-have skill", "..."],
  "min_yoe": <number of required years of experience or null>,
  "location": "<job location or null>"
}}

Rules:
- Only include must-have requirements in "skills".
- "min_yoe" must be a plain number (e.g. 3 or 2.5) or null.
- Never invent values that are not stated in the ad.

Job advertisement:
{ad_text}
"""


def _ai_distill_openrouter(ad_text: str, model_name: str, timeout_seconds: float) -> Optional[JobAdRecipe]:
    """Distill job ad using OpenRouter API. Never calls paid models."""
    import httpx

    from candidate_intelligence_platform.intelligence.chat_model import (
        OpenRouterModelPaidError,
        is_openrouter_model_free,
        mark_openrouter_model_paid,
    )

    settings = Settings()
    if not settings.openrouter_api_key:
        return None
    if not is_openrouter_model_free(model_name):
        return None

    truncated_ad = ad_text[:3000]
    prompt = _DISTILL_PROMPT.format(ad_text=truncated_ad)

    try:
        with httpx.Client(timeout=timeout_seconds) as client:
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
            response.raise_for_status()
            data = response.json()
    except OpenRouterModelPaidError:
        raise
    except Exception as e:
        logger.warning("job_ad_openrouter_request_failed", model=model_name, error=str(e))
        return None

    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
    if content and content.startswith("```"):
        content = re.sub(r"^```[a-zA-Z]*\n?", "", content)
        content = re.sub(r"\n?```$", "", content)
    try:
        parsed = json.loads(content)
    except (json.JSONDecodeError, TypeError) as e:
        logger.warning("job_ad_openrouter_json_decode_failed", model=model_name, error=str(e))
        return None
    return _coerce_recipe(parsed, ad_text, source="ai", warnings=[])


def _ai_distill_ollama(ad_text: str, model_name: str, timeout_seconds: float) -> Optional[JobAdRecipe]:
    import ollama

    truncated_ad = ad_text[:3000]
    prompt = _DISTILL_PROMPT.format(ad_text=truncated_ad)

    def _call():
        return ollama.chat(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            format="json",
        )

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        response = executor.submit(_call).result(timeout=timeout_seconds)

    content = response.message.content
    if content and content.startswith("```"):
        content = re.sub(r"^```[a-zA-Z]*\n?", "", content)
        content = re.sub(r"\n?```$", "", content)
    try:
        data = json.loads(content)
    except (json.JSONDecodeError, TypeError) as e:
        logger.warning("job_ad_ai_json_decode_failed", model=model_name, error=str(e))
        return None
    return _coerce_recipe(data, ad_text, source="ai", warnings=[])


def _ai_distill(ad_text: str, model_name: str, timeout_seconds: float) -> Optional[JobAdRecipe]:
    provider = get_llm_provider()
    if provider == "openrouter":
        return _ai_distill_openrouter(ad_text, model_name, timeout_seconds)
    return _ai_distill_ollama(ad_text, model_name, timeout_seconds)


def _extract_title_phrase(line: str) -> Optional[str]:
    """Pull just the title phrase out of a line that mentions a title hint.

    Walks left from the hint word across capitalized modifiers (seniority,
    specialization) but stops at lowercase sentence filler, so a full
    recruiting sentence never becomes the strict equality filter.
    """
    tokens = re.findall(r"[A-Za-z][A-Za-z+#./]*", line)
    for idx, token in enumerate(tokens):
        lowered = token.lower()
        if not any(hint in lowered for hint in _TITLE_HINTS):
            continue
        start = idx
        steps = 0
        while start > 0 and steps < 3:
            prev = tokens[start - 1]
            if prev.lower() in _TITLE_PHRASE_STOPS or not prev[0].isupper():
                break
            start -= 1
            steps += 1
        return " ".join(tokens[start:idx + 1])
    return None


def _fallback_extract(ad_text: str) -> Tuple[List[str], Optional[float], Optional[str], Optional[str]]:
    """Simple non-AI extraction: yoe patterns, skill-like terms, location."""
    min_yoe_values: List[float] = []
    for match in _YOE_PATTERN.finditer(ad_text):
        try:
            min_yoe_values.append(float(match.group(1)))
        except ValueError:
            continue
    min_yoe = max(min_yoe_values) if min_yoe_values else None

    counts: Dict[str, int] = {}
    order: Dict[str, int] = {}
    for index, token in enumerate(re.findall(r"[A-Za-z][A-Za-z+#]{2,}", ad_text)):
        key = token.lower()
        if key in _STOPWORDS or len(key) < 3:
            continue
        counts[key] = counts.get(key, 0) + 1
        order.setdefault(key, index)

    ranked = sorted(counts, key=lambda k: (-counts[k], order[k]))
    skills = [k.capitalize() for k in ranked[:8]]

    location = None
    loc_match = re.search(
        r"(?:location\s*[:\-]|based\s+in|located\s+in)[ \t]*([A-Z][A-Za-z\.]+(?:[ \t][A-Z][A-Za-z\.]+){0,3})",
        ad_text,
        re.IGNORECASE,
    )
    if loc_match:
        location = loc_match.group(1).strip()

    title = None
    for line in ad_text.splitlines():
        cleaned = line.strip().strip("*# ").rstrip(":")
        if not cleaned or len(cleaned) > 120:
            continue
        phrase = _extract_title_phrase(cleaned)
        if phrase:
            title = phrase
            break

    return skills, min_yoe, location, title


def _fallback_distill(ad_text: str) -> Optional[JobAdRecipe]:
    skills, min_yoe, location, title = _fallback_extract(ad_text)
    usable = bool(skills) or min_yoe is not None or bool(title)
    if not usable:
        return None
    return JobAdRecipe(
        title=title,
        skills=skills,
        min_yoe=min_yoe,
        location=location,
        summary=_build_summary(title, skills, min_yoe, ad_text),
        source="fallback",
        warnings=[
            "The online AI and this computer's built-in AI were both "
            "unavailable, so the job ad was read with basic text rules. The "
            "search may be less accurate than usual.",
        ],
    )


def _raw_distill(ad_text: str) -> JobAdRecipe:
    return JobAdRecipe(
        title=None,
        skills=[],
        min_yoe=None,
        location=None,
        summary=_truncate_summary(ad_text),
        source="raw",
        warnings=[
            "This job ad couldn't be analyzed automatically. We're searching "
            "the pasted text directly instead.",
        ],
    )


def distill_job_ad(ad_text: str, timeout_seconds: float = 45.0) -> JobAdRecipe:
    """Distill a pasted job ad: configured provider first, local Ollama second, heuristics third, raw last."""
    text = (ad_text or "").strip()
    settings = Settings()

    try:
        model_name = resolve_chat_model()
    except Exception as e:
        logger.warning("job_ad_chat_model_probe_failed", error=str(e))
        model_name = None

    if model_name:
        try:
            recipe = _ai_distill(text, model_name, timeout_seconds)
            if recipe is not None:
                return recipe
            logger.warning("job_ad_ai_distill_unusable", model=model_name, action="falling_back_to_local_heuristics")
        except Exception as e:
            logger.warning(
                "job_ad_ai_distill_failed",
                model=model_name,
                error=str(e),
                action="falling_back_then_local_heuristics",
            )

    # Provider failed (e.g. OpenRouter went paid) -> one direct Ollama attempt.
    if get_llm_provider() == "openrouter":
        try:
            ollama_model = settings.llm_model
            recipe = _ai_distill_ollama(text, ollama_model, timeout_seconds)
            if recipe is not None:
                logger.error(
                    "*** JOB AD FALLBACK ACTIVE ***",
                    skipped_model=settings.openrouter_model,
                    fallback_model=ollama_model,
                    reason="openrouter_unavailable_or_paid",
                )
                recipe.warnings.append(
                    "The online AI wasn't reachable, so this job ad was read by "
                    "this computer's built-in AI instead."
                )
                return recipe
        except Exception as e:
            logger.warning("job_ad_ollama_retry_failed", model=settings.llm_model, error=str(e))

    recipe = _fallback_distill(text)
    if recipe is not None:
        return recipe

    return _raw_distill(text)


def build_search_dsl(recipe: JobAdRecipe) -> str:
    """Compose the distilled recipe into parser-compatible DSL."""
    parts: List[str] = []
    keyword_terms = [re.sub(r"[^\w+#.\-]", " ", skill).strip() for skill in recipe.skills]
    keyword_terms = [term for term in keyword_terms if term]
    if keyword_terms:
        parts.append(" ".join(keyword_terms[:10]))
    if recipe.title:
        safe_title = recipe.title.replace("'", "")
        parts.append(f"title:'{safe_title}'")
    if recipe.location:
        safe_location = recipe.location.replace("'", "")
        parts.append(f"location:'{safe_location}'")
    if recipe.min_yoe is not None:
        formatted = f"{recipe.min_yoe:g}"
        parts.append(f"yoe >= {formatted}")
    return " AND ".join(parts)
