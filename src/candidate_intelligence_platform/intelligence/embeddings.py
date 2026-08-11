from fastembed import TextEmbedding

embedding_model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")

def generate_embeddings(texts: list[str]) -> list[list[float]]:
    """
    Generate dense vector embeddings for a list of texts using fastembed.
    Returns 384-dimensional vectors.
    """
    embeddings_gen = embedding_model.embed(texts)
    return [list(map(float, emb)) for emb in embeddings_gen]
