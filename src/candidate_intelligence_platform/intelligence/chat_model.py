"""Resolve the configured chat/explainer LLM to an actually available Ollama model.

Resolution order:
1. The configured Settings.llm_model (if installed locally).
2. Settings.fallback_llm_model (llama3.2) when the configured name is invalid or missing.
3. None when no usable chat model exists; callers must degrade gracefully
   (search results stay unaffected, a visible AI-explanation-unavailable message is shown).
"""
import threading
import time
import structlog

from config.settings import Settings

logger = structlog.get_logger(__name__)

LAST_RESORT_CHAT_MODEL = "llama3.2"

_PROBE_TTL_SECONDS = 30.0

_cache_lock = threading.Lock()
_cached_model: str | None = None
_cached_at: float = -1.0


def normalize_model_name(name: str) -> str:
    """Strip the tag suffix so 'llama3.2' matches 'llama3.2:latest'."""
    return (name or "").split(":", 1)[0].strip().lower()


def chat_retry_candidates(llm_model: str, fallback_llm_model: str, failed_model: str | None = None) -> list[str]:
    """Ordered chat models to try after the primary fails.

    Chain: Settings.fallback_llm_model, then the guaranteed llama3.2 last resort,
    skipping anything equal (by normalized name) to the failed model.
    """
    ordered = [fallback_llm_model, LAST_RESORT_CHAT_MODEL]
    base = failed_model or llm_model
    seen = {normalize_model_name(base)}
    candidates: list[str] = []
    for name in ordered:
        normalized = normalize_model_name(name)
        if name and normalized and normalized not in seen:
            seen.add(normalized)
            candidates.append(name)
    return candidates


def _installed_model_names() -> list[str]:
    """Return normalized names of models installed in the local Ollama instance."""
    import ollama
    
    response = ollama.list()
    if isinstance(response, dict):
        raw_models = response.get("models", [])
    else:
        raw_models = getattr(response, "models", [])
    
    names = []
    for entry in raw_models:
        if isinstance(entry, dict):
            name = entry.get("model") or entry.get("name") or ""
        else:
            name = getattr(entry, "model", "") or getattr(entry, "name", "")
        normalized = normalize_model_name(str(name))
        if normalized:
            names.append(normalized)
    return names


def resolve_chat_model(force_refresh: bool = False) -> str | None:
    """Return an available chat model name, or None when none is usable.

    Result is cached briefly (_PROBE_TTL_SECONDS) so search requests do not
    re-probe Ollama on every call.
    """
    global _cached_model, _cached_at
    
    with _cache_lock:
        now = time.monotonic()
        if not force_refresh and _cached_at >= 0.0 and (now - _cached_at) < _PROBE_TTL_SECONDS:
            return _cached_model
        
        settings = Settings()
        try:
            installed = _installed_model_names()
        except Exception as e:
            logger.warning(
                "ai_chat_probe_failed",
                error=str(e),
                action="treating_all_chat_models_as_unavailable"
            )
            installed = []
        
        resolved: str | None = None
        configured = settings.llm_model
        
        chain = [settings.llm_model, *chat_retry_candidates(settings.llm_model, settings.fallback_llm_model)]
        for candidate in chain:
            if normalize_model_name(candidate) in installed:
                if candidate != configured:
                    logger.warning(
                        "ai_chat_model_fallback",
                        configured_model=configured,
                        fallback_model=candidate,
                        reason="configured_chat_model_not_installed"
                    )
                resolved = candidate
                break
        
        if resolved is None:
            logger.warning(
                "ai_chat_unavailable",
                configured_model=configured,
                fallback_model=settings.fallback_llm_model,
                installed=installed,
                action="serving_results_without_ai_explanations"
            )
        
        _cached_model = resolved
        _cached_at = now
        return resolved


def reset_chat_model_cache() -> None:
    """Clear the cached resolution (used by tests)."""
    global _cached_model, _cached_at
    with _cache_lock:
        _cached_model = None
        _cached_at = -1.0
