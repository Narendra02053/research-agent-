"""
config.py
Centralized configuration management using Pydantic Settings.
Loads configuration from environment variables (.env).
"""
import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # API Keys
    TAVILY_API_KEY: str = ""
    GROQ_API_KEY: str = ""

    # Infrastructure
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333

    # Application Settings
    ENVIRONMENT: str = "development" # development | staging | production
    LOG_LEVEL: str = "INFO"
    
    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW_SECS: int = 60

    # Model defaults
    DEFAULT_LLM_MODEL: str = "llama-3.1-70b-versatile"
    DEFAULT_EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"

    # LLM Providers
    OPENAI_API_KEY: str = ""
    OLLAMA_BASE_URL: str = "http://localhost:11434"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"


# Instantiate global settings object
settings = Settings()
