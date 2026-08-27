from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="APP_", env_file=".env", extra="ignore")

    database_url: str = "sqlite+aiosqlite:///./calls.db"
    upload_dir: Path = Path("data/uploads")
    max_upload_bytes: int = 50 * 1024 * 1024
    whisper_model: str = "small"
    whisper_device: str = "cpu"
    whisper_compute_type: str = "int8"
    ollama_url: str = "http://ollama:11434"
    ollama_model: str = "qwen3:8b"
    ollama_embedding_model: str = "nomic-embed-text"
    embedding_dimensions: int = 768
    celery_broker_url: str = "redis://redis:6379/0"
    celery_result_backend: str = "redis://redis:6379/1"


@lru_cache
def get_settings() -> Settings:
    return Settings()
