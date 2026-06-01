"""Application configuration using pydantic-settings."""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Gemini API
    gemini_api_key: str = ""

    # Database — Supabase PostgreSQL connection string
    # Format: postgresql+asyncpg://user:pass@host:port/dbname
    database_url: str = ""

    # Supabase (optional — for future direct Supabase client features)
    supabase_url: str = ""
    supabase_key: str = ""

    # Embedding Model
    embedding_model: str = "all-MiniLM-L6-v2"

    # RAG Settings
    chunk_size: int = 500
    chunk_overlap: int = 100
    top_k: int = 8

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # Gemini Model
    gemini_model: str = "gemini-2.5-flash"

    # CORS — set to your frontend URL in production
    frontend_url: str = ""

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
    }


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
