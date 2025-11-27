# config/settings.py
import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    QDRANT_URL: str = os.getenv("QDRANT_URL", "http://127.0.0.1:6333")
    QDRANT_COLLECTION: str = os.getenv("QDRANT_COLLECTION", "kb_chunks")
    OLLAMA_URL: str = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gemma3:4b")
    EMBED_MODEL: str = os.getenv("EMBED_MODEL", "intfloat/multilingual-e5-small")
    TOP_K: int = int(os.getenv("TOP_K", 6))

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
