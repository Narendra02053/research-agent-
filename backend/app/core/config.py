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

    # Research pipeline performance (disable heavy steps for faster responses)
    ENABLE_KNOWLEDGE_GRAPH: bool = False
    SKIP_EVALUATION: bool = True
    MAX_SEARCH_SUBQUERIES: int = 2       # was 3 — fewer parallel Tavily calls
    MAX_EXTRACTION_URLS: int = 3         # was 5 — fewer pages to scrape & embed
    MAX_KG_CHUNKS: int = 2
    RETRIEVAL_CHUNK_LIMIT: int = 5       # was 8
    RERANK_TOP_K: int = 4                # was 5
    MAX_CONTEXT_CHARS: int = 12000       # hard cap on context sent to LLM

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
