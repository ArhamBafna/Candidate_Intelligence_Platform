from fastembed.rerank.cross_encoder import TextCrossEncoder

# Using the MS MARCO model specified in the architecture document
reranker_model = TextCrossEncoder(model_name="Xenova/ms-marco-MiniLM-L-6-v2")

def rerank_candidates(query: str, documents: list[str]) -> list[float]:
    """
    Reranks a list of documents based on a query using a cross-encoder model.
    Returns a list of relevance scores (floats) corresponding to the documents.
    """
    # model.rerank returns a generator of numpy arrays or floats.
    # We consume it into a list of floats.
    scores_gen = reranker_model.rerank(query, documents)
    
    # fastembed rerank might return a single list or generator of floats/arrays.
    # We flatten it to a list of floats.
    scores = list(scores_gen)
    
    # If it returns numpy arrays per element, we extract the float.
    # In some versions of fastembed, it returns a generator of generators/arrays.
    if scores and hasattr(scores[0], '__iter__'):
        return [float(score[0]) if len(score) > 0 else 0.0 for score in scores]
    return [float(score) for score in scores]
