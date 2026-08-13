import pytest
import os
from storage.vector_store import get_lancedb_connection, CandidateSectionVector

def test_lancedb_initialization(tmp_path):
    """Verify LanceDB connection and table initialization."""
    db_path = str(tmp_path / "lancedb")
    
    db = get_lancedb_connection(db_path)
    
    # Initialize or get the table
    table = db.create_table(
        "candidate_sections", 
        schema=CandidateSectionVector, 
        exist_ok=True
    )
    
    assert table.name == "candidate_sections"
    assert "chunk_id" in table.schema.names
    assert "vector" in table.schema.names


def test_vector_store_embedding_search(tmp_path):
    """End-to-end test verifying embedding generation, LanceDB storage, and vector similarity retrieval."""
    from candidate_intelligence_platform.intelligence.embeddings import generate_embeddings

    db_path = str(tmp_path / "lancedb_search_test")
    db = get_lancedb_connection(db_path)
    
    table = db.create_table(
        "candidate_vectors",
        schema=CandidateSectionVector,
        exist_ok=True
    )
    
    sections = [
        "Senior Cloud Architect with AWS, Kubernetes, Terraform, and Docker expertise.",
        "Sales Associate with 3 years experience in retail and customer service.",
        "Full Stack Developer proficient in Python, React, PostgreSQL, and GraphQL."
    ]
    embeddings = generate_embeddings(sections)
    
    records = []
    for idx, (text_content, emb) in enumerate(zip(sections, embeddings)):
        records.append({
            "chunk_id": f"chunk-{idx}",
            "candidate_id": f"cand-{idx}",
            "resume_version_id": f"res-{idx}",
            "section_type": "WORK_EXPERIENCE",
            "chunk_text": text_content,
            "vector": emb,
            "start_offset": 0,
            "end_offset": len(text_content)
        })
        
    table.add(records)
    
    # Query vector search for "Kubernetes Cloud DevOps"
    query_emb = generate_embeddings(["Kubernetes Cloud DevOps infrastructure"])[0]
    results = table.search(query_emb).limit(2).to_list()
    
    assert len(results) > 0
    # The top matching record should be candidate 0 (Cloud Architect)
    assert results[0]["candidate_id"] == "cand-0"
    assert "Kubernetes" in results[0]["chunk_text"]

