import os
from pydantic_settings import BaseSettings

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class Settings(BaseSettings):
    db_path: str = os.path.join(BASE_DIR, "storage", "cip_main.db")
    cas_root_dir: str = os.path.join(BASE_DIR, "storage", "documents")
    vector_db_path: str = os.path.join(BASE_DIR, "storage", "lancedb")
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    llm_model: str = "llama3.2"
    extraction_confidence_threshold: float = 0.40
    entity_res_auto_merge_threshold: float = 0.85
    entity_res_review_threshold: float = 0.70

    model_config = {"env_prefix": "CIP_"}
