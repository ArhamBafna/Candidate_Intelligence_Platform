"""Lazy-loaded embedding model for vector search with GPU auto-detect.

Model: BAAI/bge-small-en-v1.5 (384-dimensional embeddings)
"""
import threading
import functools
import structlog

logger = structlog.get_logger(__name__)

_embedding_model = None
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


def _get_embedding_model():
    """Lazy-load the embedding model on first use (thread-safe, GPU with CPU fallback)."""
    global _embedding_model
    if _embedding_model is None:
        with _embedding_lock:
            if _embedding_model is None:
                from fastembed import TextEmbedding
                
                use_gpu = _check_gpu_available()
                providers = ["CUDAExecutionProvider", "CPUExecutionProvider"] if use_gpu else None
                
                try:
                    if providers:
                        _embedding_model = TextEmbedding(
                            model_name="BAAI/bge-small-en-v1.5",
                            providers=providers
                        )
                        logger.info("embedding_model_loaded", gpu=True)
                    else:
                        _embedding_model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
                        logger.info("embedding_model_loaded", gpu=False)
                except Exception as e:
                    # Fallback to CPU if GPU loading fails
                    logger.warning("gpu_fallback", error=str(e), fallback="cpu")
                    _embedding_model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
    
    return _embedding_model


@functools.lru_cache(maxsize=1024)
def generate_single_embedding(text: str) -> list[float]:
    """Generate a single embedding vector (cached for repeated queries)."""
    model = _get_embedding_model()
    embeddings_gen = model.embed([text])
    return [float(x) for x in next(embeddings_gen)]


def generate_embeddings(texts: list[str]) -> list[list[float]]:
    """
    Generate dense vector embeddings for a list of texts using fastembed.
    Returns 384-dimensional vectors.
    """
    if not texts:
        return []
    
    model = _get_embedding_model()
    embeddings_gen = model.embed(texts)
    return [list(map(float, emb)) for emb in embeddings_gen]
