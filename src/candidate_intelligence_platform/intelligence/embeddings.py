"""Lazy-loaded embedding model for vector search with GPU auto-detect.

Default model: BAAI/bge-small-en-v1.5 (384-dimensional embeddings)
Configurable via the CIP_EMBEDDING_MODEL environment variable / Settings.embedding_model.
An invalid or unavailable model name falls back to the documented default.
"""
import threading
import functools
from typing import Any
import structlog

from config.settings import get_settings

logger = structlog.get_logger(__name__)

DEFAULT_EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"

_embedding_model = None
_embedding_model_name = None
_embedding_lock = threading.Lock()
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


def _load_text_embedding(model_name: str) -> "TextEmbedding":
    from fastembed import TextEmbedding
    
    use_gpu = _check_gpu_available()
    providers = ["CUDAExecutionProvider", "CPUExecutionProvider"] if use_gpu else None
    
    try:
        if providers:
            model = TextEmbedding(model_name=model_name, providers=providers)
            logger.info("embedding_model_loaded", model=model_name, gpu=True)
        else:
            model = TextEmbedding(model_name=model_name)
            logger.info("embedding_model_loaded", model=model_name, gpu=False)
        return model
    except Exception as e:
        logger.warning("gpu_fallback", error=str(e), fallback="cpu")
        return TextEmbedding(model_name=model_name)


def _get_embedding_model() -> Any:
    """Lazy-load the embedding model on first use (thread-safe).

    Loads the configured Settings.embedding_model; if that name is invalid or
    unavailable, logs a warning and loads the documented default instead.
    """
    global _embedding_model, _embedding_model_name
    if _embedding_model is None:
        with _embedding_lock:
            if _embedding_model is None:
                configured_model = get_settings().embedding_model
                
                try:
                    _embedding_model = _load_text_embedding(configured_model)
                    _embedding_model_name = configured_model
                except Exception as e:
                    logger.warning(
                        "ai_embedding_model_fallback",
                        configured_model=configured_model,
                        error=str(e),
                        fallback_model=DEFAULT_EMBEDDING_MODEL,
                        action="loading_documented_default"
                    )
                    _embedding_model = _load_text_embedding(DEFAULT_EMBEDDING_MODEL)
                    _embedding_model_name = DEFAULT_EMBEDDING_MODEL
    
    return _embedding_model


def get_embedding_model_name() -> str:
    """Return the name of the currently loaded embedding model."""
    if _embedding_model is None:
        _get_embedding_model()
    assert _embedding_model_name is not None
    return _embedding_model_name


@functools.lru_cache(maxsize=1024)
def generate_single_embedding(text: str) -> list[float]:
    """Generate a single embedding vector (cached for repeated queries)."""
    model = _get_embedding_model()
    embeddings_gen = model.embed([text])
    return [float(x) for x in next(embeddings_gen)]


def generate_embeddings(texts: list[str]) -> list[list[float]]:
    """
    Generate dense vector embeddings for a list of texts using fastembed.
    Returns vectors matching the loaded model's dimensionality (384 for the default).
    """
    if not texts:
        return []
    
    model = _get_embedding_model()
    embeddings_gen = model.embed(texts)
    return [list(map(float, emb)) for emb in embeddings_gen]
