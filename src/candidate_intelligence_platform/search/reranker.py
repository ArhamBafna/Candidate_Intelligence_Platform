"""Lazy-loaded cross-encoder reranker for search results with GPU auto-detect.

Model: Xenova/ms-marco-MiniLM-L-6-v2 (MS MARCO passage ranking)
"""
import threading
import structlog

logger = structlog.get_logger(__name__)

_reranker_model = None
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


def _get_reranker():
    """Lazy-load the cross-encoder model on first use (thread-safe, GPU with CPU fallback)."""
    global _reranker_model
    if _reranker_model is None:
        with _reranker_lock:
            if _reranker_model is None:
                from fastembed.rerank.cross_encoder import TextCrossEncoder
                
                use_gpu = _check_gpu_available()
                providers = ["CUDAExecutionProvider", "CPUExecutionProvider"] if use_gpu else None
                
                try:
                    if providers:
                        _reranker_model = TextCrossEncoder(
                            model_name="Xenova/ms-marco-MiniLM-L-6-v2",
                            providers=providers
                        )
                        logger.info("reranker_model_loaded", gpu=True)
                    else:
                        _reranker_model = TextCrossEncoder(model_name="Xenova/ms-marco-MiniLM-L-6-v2")
                        logger.info("reranker_model_loaded", gpu=False)
                except Exception as e:
                    # Fallback to CPU if GPU loading fails
                    logger.warning("gpu_fallback", error=str(e), fallback="cpu")
                    _reranker_model = TextCrossEncoder(model_name="Xenova/ms-marco-MiniLM-L-6-v2")
    
    return _reranker_model


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
