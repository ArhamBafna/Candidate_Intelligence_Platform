from fastembed import TextEmbedding
import functools

embedding_model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")

@functools.lru_cache(maxsize=1024)
def generate_single_embedding(text: str) -> list[float]:
    embeddings_gen = embedding_model.embed([text])
    return [float(x) for x in next(embeddings_gen)]

def generate_embeddings(texts: list[str]) -> list[list[float]]:
    """
    Generate dense vector embeddings for a list of texts using fastembed.
    Returns 384-dimensional vectors.
    """
    embeddings_gen = embedding_model.embed(texts)
    return [list(map(float, emb)) for emb in embeddings_gen]
