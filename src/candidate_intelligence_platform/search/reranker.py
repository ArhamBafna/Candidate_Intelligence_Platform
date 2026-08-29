"""Lazy-loaded cross-encoder reranker for search results with GPU auto-detect.

Default model: Xenova/ms-marco-MiniLM-L-6-v2 (MS MARCO passage ranking)
Configurable via the CIP_RERANKER_MODEL environment variable / Settings.reranker_model.
An invalid or unavailable model name falls back to the documented default.
"""
import threading
from typing import Any
import structlog

from config.settings import get_settings

logger = structlog.get_logger(__name__)

DEFAULT_RERANKER_MODEL = "Xenova/ms-marco-MiniLM-L-6-v2"

_reranker_model = None
_reranker_model_name = None
_reranker_lock = threading.Lock()
_gpu_available = None


def _check_gpu_available() -> bool:
    """Check if GPU (CUDA) is available for acceleration."""
    global _gpu_available
    if _gpu_available is not None:
        return _gpu_available
    
    try:
        import onnxruntime as ort
        providers = ort.get_available_providers()
        _gpu_available = "CUDAExecutionProvider" in providers
        if _gpu_available:
            logger.info("gpu_available", provider="CUDAExecutionProvider")
        else:
            logger.info("gpu_unavailable", available_providers=providers)
    except ImportError:
        _gpu_available = False
        logger.info("gpu_unavailable", reason="onnxruntime not installed")
    
    return _gpu_available


def _load_text_cross_encoder(model_name: str) -> "TextCrossEncoder":
    from fastembed.rerank.cross_encoder import TextCrossEncoder
    
    use_gpu = _check_gpu_available()
    providers = ["CUDAExecutionProvider", "CPUExecutionProvider"] if use_gpu else None
    
    try:
        if providers:
            model = TextCrossEncoder(model_name=model_name, providers=providers)
            logger.info("reranker_model_loaded", model=model_name, gpu=True)
        else:
            model = TextCrossEncoder(model_name=model_name)
            logger.info("reranker_model_loaded", model=model_name, gpu=False)
        return model
    except Exception as e:
        logger.warning("gpu_fallback", error=str(e), fallback="cpu")
        return TextCrossEncoder(model_name=model_name)


def _get_reranker() -> Any:
    """Lazy-load the cross-encoder model on first use (thread-safe).

    Loads the configured Settings.reranker_model; if that name is invalid or
    unavailable, logs a warning and loads the documented default instead.
    """
    global _reranker_model, _reranker_model_name
    if _reranker_model is None:
        with _reranker_lock:
            if _reranker_model is None:
                configured_model = get_settings().reranker_model
                
                try:
                    _reranker_model = _load_text_cross_encoder(configured_model)
                    _reranker_model_name = configured_model
                except Exception as e:
                    logger.warning(
                        "ai_reranker_model_fallback",
                        configured_model=configured_model,
                        error=str(e),
                        fallback_model=DEFAULT_RERANKER_MODEL,
                        action="loading_documented_default"
                    )
                    _reranker_model = _load_text_cross_encoder(DEFAULT_RERANKER_MODEL)
                    _reranker_model_name = DEFAULT_RERANKER_MODEL
    
    return _reranker_model


def get_reranker_model_name() -> str:
    """Return the name of the currently loaded reranker model."""
    if _reranker_model is None:
        _get_reranker()
    assert _reranker_model_name is not None
    return _reranker_model_name


def rerank_candidates(query: str, documents: list[str]) -> list[float]:
    """
    Reranks a list of documents based on a query using a cross-encoder model.
    Returns a list of relevance scores (floats) corresponding to the documents.
    """
    if not documents:
        return []
    
    reranker = _get_reranker()
    
    # model.rerank returns a generator of numpy arrays or floats.
    # We consume it into a list of floats.
    scores_gen = reranker.rerank(query, documents)
    
    # fastembed rerank might return a single list or generator of floats/arrays.
    # We flatten it to a list of floats.
    scores = list(scores_gen)
    
    # If it returns numpy arrays per element, we extract the float.
    # In some versions of fastembed, it returns a generator of generators/arrays.
    if scores and hasattr(scores[0], '__iter__'):
        return [float(score[0]) if len(score) > 0 else 0.0 for score in scores]
    return [float(score) for score in scores]
