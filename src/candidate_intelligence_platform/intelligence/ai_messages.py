"""Recruiter-friendly AI status messages shown in the interface.

Keep every string free of internal jargon (no provider or file names).
"Cloud AI" = online assistant. "On-device AI" = private AI on this computer.
"""

CLOUD_AI_LABEL = "Cloud AI"
DEVICE_AI_LABEL = "this computer's built-in AI"

AI_EXPLANATION_UNAVAILABLE = (
    "AI explanations are taking a break right now - we couldn't reach the "
    "online AI and this computer's built-in AI is busy too. Your search "
    "results are completely unaffected."
)

CLOUD_FALLBACK_TO_DEVICE = (
    "Heads up: the online AI couldn't be reached, so these notes were written "
    "by this computer's built-in AI instead."
)

ONLINE_AI_NOW_PAID = (
    "The online AI assistant was switched off because it started charging "
    "money. Everything now runs on this computer's built-in AI - still "
    "completely private."
)

DEVICE_FALLBACK_NOTICE = (
    "Your chosen AI model isn't set up on this computer, so the backup AI "
    "(Llama 3.2) answered instead."
)


def label_for_model(model_name: str) -> str:
    """Human name for a model id. 'vendor/model' ids read as Cloud AI."""
    if not model_name:
        return DEVICE_AI_LABEL
    return CLOUD_AI_LABEL if "/" in model_name else f"On-device AI ({model_name})"
