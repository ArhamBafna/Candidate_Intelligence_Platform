import pytest
from candidate_intelligence_platform.intelligence.embeddings import generate_embeddings

def test_generate_embeddings():
    texts = ["Hello world", "Machine learning engineer with 5 years experience"]
    embeddings = generate_embeddings(texts)
    
    assert len(embeddings) == 2
    assert len(embeddings[0]) == 384
    assert len(embeddings[1]) == 384
    assert isinstance(embeddings[0][0], float)
