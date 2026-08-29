"""Resolve the configured chat/explainer LLM to an actually available model.

Resolution order:
1. OpenRouter (stealth/ox-alpha) when provider=openrouter AND the model is
   verified FREE on OpenRouter. Paid models are never called.
2. The configured Ollama model (Settings.llm_model) if installed locally.
3. Settings.fallback_llm_model (llama3.2) when the configured name is invalid.
4. None when no usable chat model exists; callers must degrade gracefully.

Free-only rule for OpenRouter:
- Pricing is checked via GET /api/v1/models before any generation request.
- free  -> continue using ox-alpha
- paid  -> instantly stop; loud error logged; fall back to local Ollama
- a 402 Payment Required during any request marks the model paid immediately.
"""
import threading
import time
import structlog

from config.settings import get_settings

logger = structlog.get_logger(__name__)

LAST_RESORT_CHAT_MODEL = "llama3.2"

_PROBE_TTL_SECONDS = 30.0

_PRICING_TTL_SECONDS = 600.0

_cache_lock = threading.Lock()
_cached_model: str | None = None
_cached_at: float = -1.0

_pricing_lock = threading.Lock()
_pricing_free: dict[str, bool] = {}
_pricing_checked_at: float = -1.0


class OpenRouterModelPaidError(RuntimeError):
    """Raised when an OpenRouter request is refused because the model is not free."""


def normalize_model_name(name: str) -> str:
    """Strip the tag suffix so 'llama3.2' matches 'llama3.2:latest'."""
    return (name or "").split(":", 1)[0].strip().lower()


def chat_retry_candidates(
    llm_model: str, fallback_llm_model: str, failed_model: str | None = None
) -> list[str]:
    """Ordered chat models to try after the primary fails."""
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


def _installed_ollama_model_names() -> list[str]:
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


def mark_openrouter_model_paid(model_name: str) -> None:
    """Instantly blacklist a model as paid after a 402 or price change."""
    global _pricing_checked_at
    with _pricing_lock:
        _pricing_free[model_name] = False
        _pricing_checked_at = time.monotonic()
    logger.error(
        "OPENROUTER_MODEL_NOW_PAID_STOPPED",
        model=model_name,
        action="model_blacklisted_falling_back_to_local_ollama",
        detail="OpenRouter model is no longer free. All OpenRouter calls for "
        "this model are stopped immediately.",
    )


def is_openrouter_model_free(model_name: str, force_refresh: bool = False) -> bool:
    """True only when OpenRouter reports zero prompt+completion price.

    Fail-closed: unknown model, missing pricing, or network error => NOT free.
    """
    global _pricing_free, _pricing_checked_at

    if not model_name:
        return False

    with _pricing_lock:
        now = time.monotonic()
        cache_valid = (
            not force_refresh
            and _pricing_checked_at >= 0.0
            and (now - _pricing_checked_at) < _PRICING_TTL_SECONDS
            and model_name in _pricing_free
        )
        if cache_valid:
            return _pricing_free[model_name]

    try:
        import httpx

        settings = get_settings()
        response = httpx.get(
            f"{settings.openrouter_base_url}/models",
            timeout=10.0,
        )
        response.raise_for_status()
        models = response.json().get("data", [])
        entry = next((m for m in models if m.get("id") == model_name), None)
        if entry is None:
            logger.error(
                "OPENROUTER_MODEL_NOT_FOUND",
                model=model_name,
                action="treating_as_paid_falling_back_to_ollama",
            )
            is_free = False
        else:
            pricing = entry.get("pricing", {}) or {}
            try:
                prompt_price = float(pricing.get("prompt", "inf"))
                completion_price = float(pricing.get("completion", "inf"))
            except (TypeError, ValueError):
                prompt_price = float("inf")
                completion_price = float("inf")
            is_free = prompt_price == 0.0 and completion_price == 0.0
    except Exception as e:
        logger.error(
            "OPENROUTER_PRICING_CHECK_FAILED",
            model=model_name,
            error=str(e),
            action="treating_as_paid_falling_back_to_ollama",
        )
        is_free = False

    with _pricing_lock:
        _pricing_free[model_name] = is_free
        _pricing_checked_at = time.monotonic()

    return is_free


def reset_openrouter_pricing_cache() -> None:
    """Clear cached pricing verdicts (used by tests)."""
    global _pricing_free, _pricing_checked_at
    with _pricing_lock:
        _pricing_free = {}
        _pricing_checked_at = -1.0


def get_llm_provider() -> str:
    """Effective provider. API key is IGNORED unless provider=openrouter."""
    settings = get_settings()
    provider = settings.llm_provider.lower()

    if provider != "openrouter":
        if settings.openrouter_api_key:
            logger.warning(
                "openrouter_api_key_ignored",
                reason="CIP_LLM_PROVIDER is not 'openrouter'; key present but unused",
            )
        return "ollama"

    if not settings.openrouter_api_key:
        logger.warning(
            "openrouter_api_key_missing",
            action="falling_back_to_ollama",
        )
        return "ollama"

    return "openrouter"


def resolve_chat_model(force_refresh: bool = False) -> str | None:
    """Return an available chat model name, or None when none is usable."""
    global _cached_model, _cached_at

    with _cache_lock:
        now = time.monotonic()
        if not force_refresh and _cached_at >= 0.0 and (now - _cached_at) < _PROBE_TTL_SECONDS:
            return _cached_model

        settings = get_settings()
        provider = settings.llm_provider.lower()
        resolved: str | None = None

        if provider == "openrouter":
            if not settings.openrouter_api_key:
                logger.warning(
                    "ai_chat_openrouter_no_key",
                    action="falling_back_to_ollama",
                )
                provider = "ollama"
            elif not is_openrouter_model_free(settings.openrouter_model):
                # Loud log emitted inside the pricing check / mark helper.
                logger.error(
                    "OPENROUTER_FALLBACK_TO_OLLAMA",
                    configured_model=settings.openrouter_model,
                    reason="model_not_free_or_unverified",
                    action="using_local_ollama_instead",
                )
                provider = "ollama"
            else:
                resolved = settings.openrouter_model

        if resolved is None and provider == "ollama":
            try:
                installed = _installed_ollama_model_names()
            except Exception as e:
                logger.warning(
                    "ai_chat_probe_failed",
                    error=str(e),
                    action="treating_all_chat_models_as_unavailable",
                )
                installed = []

            configured = settings.llm_model
            chain = [
                settings.llm_model,
                *chat_retry_candidates(settings.llm_model, settings.fallback_llm_model),
            ]
            for candidate in chain:
                if normalize_model_name(candidate) in installed:
                    if candidate != configured:
                        logger.error(
                            "*** OLLAMA FALLBACK ACTIVE ***",
                            configured_model=configured,
                            fallback_model=candidate,
                            reason="configured_chat_model_not_installed_locally",
                            action=f"serving_with_{candidate}_instead_of_{configured}",
                        )
                    else:
                        logger.info("ai_chat_model_resolved", model=candidate)
                    resolved = candidate
                    break

            if resolved is None:
                logger.error(
                    "AI_CHAT_UNAVAILABLE",
                    configured_model=configured,
                    fallback_model=settings.fallback_llm_model,
                    installed=installed,
                    action="serving_results_without_ai_explanations",
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