"""
config.py — Application configuration via environment variables.

Uses pydantic-settings so all env vars are validated at startup.
In development, values are loaded from a .env file.
In production (Render/Railway), set them as platform environment variables.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # -----------------------------------------------------------------------
    # Supabase
    # -----------------------------------------------------------------------
    supabase_url: str
    supabase_anon_key: str
    supabase_service_role_key: str

    # Direct Postgres connection string (with pgvector extension enabled)
    # Format: postgresql+asyncpg://user:password@host:5432/dbname
    database_url: str

    # -----------------------------------------------------------------------
    # Groq (LLM for RAG chat)
    # -----------------------------------------------------------------------
    groq_api_key: str
    groq_model: str = "llama-3.3-70b-versatile"  # swap for llama-3.1-8b-instant if needed

    # -----------------------------------------------------------------------
    # App
    # -----------------------------------------------------------------------
    environment: str = "development"
    cors_origins: str = "http://localhost:3000"  # comma-separated list

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


# Import this singleton throughout the app: `from app.config import settings`
settings = Settings()  # type: ignore[call-arg]
