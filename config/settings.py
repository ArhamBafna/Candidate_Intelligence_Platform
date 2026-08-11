from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    db_path: str = "storage/cip_main.db"
    cas_root_dir: str = "storage/documents"
    vector_db_path: str = "storage/lancedb"
    backup_dir: str = "backups_data"
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    entity_resolution_auto_merge_threshold: float = 0.92
    
    model_config = {"env_prefix": "CIP_"}
