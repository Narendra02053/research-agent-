"""
config.py
Centralized configuration management using Pydantic Settings v2.
Validates all required environment variables at startup.
Separates configuration into typed sub-models for each domain.
Fail-fast if critical variables are missing.
"""

import os
from typing import Optional, Literal
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="", extra="ignore")

    DEFAULT_LLM_MODEL: str = "llama-3.1-70b-versatile"
    DEFAULT_EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"

    GROQ_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    OLLAMA_BASE_URL: str = "http://localhost:11434"

    @field_validator("GROQ_API_KEY")
    @classmethod
    def validate_groq_key(cls, v: str) -> str:
        if v and v == "your_key_here":
            raise ValueError("GROQ_API_KEY is set to placeholder 'your_key_here'")
        return v

    @field_validator("OPENAI_API_KEY")
    @classmethod
    def validate_openai_key(cls, v: str) -> str:
        if v and v == "your_key_here":
            raise ValueError("OPENAI_API_KEY is set to placeholder 'your_key_here'")
        return v

    def is_groq_available(self) -> bool:
        return bool(self.GROQ_API_KEY)

    def is_openai_available(self) -> bool:
        return bool(self.OPENAI_API_KEY)


class RedisSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="", extra="ignore")

    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None
    REDIS_SSL: bool = False
    REDIS_SOCKET_TIMEOUT: int = 5
    REDIS_RETRY_ATTEMPTS: int = 3
    REDIS_RETRY_DELAY: float = 0.5

    @property
    def redis_url(self) -> str:
        scheme = "rediss" if self.REDIS_SSL else "redis"
        if self.REDIS_PASSWORD:
            return f"{scheme}://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"{scheme}://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"


class QdrantSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="", extra="ignore")

    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_API_KEY: Optional[str] = None
    QDRANT_HTTPS: bool = False
    QDRANT_COLLECTION: str = "research_docs"
    QDRANT_VECTOR_SIZE: int = 384

    @property
    def qdrant_url(self) -> str:
        return f"https://{self.QDRANT_HOST}:{self.QDRANT_PORT}" if self.QDRANT_HTTPS else f"http://{self.QDRANT_HOST}:{self.QDRANT_PORT}"


class SecuritySettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="", extra="ignore")

    JWT_SECRET_KEY: str = ""
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 24
    API_KEY_HASH_SALT: str = ""
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW_SECS: int = 60

    @field_validator("JWT_SECRET_KEY")
    @classmethod
    def validate_jwt_secret(cls, v: str) -> str:
        env = os.getenv("ENVIRONMENT", "development")
        if env == "production" and not v:
            raise ValueError("JWT_SECRET_KEY is required in production")
        if not v:
            return "dev-insecure-change-me"
        return v


class TavilySettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="", extra="ignore")

    TAVILY_API_KEY: str = ""

    @field_validator("TAVILY_API_KEY")
    @classmethod
    def validate_tavily_key(cls, v: str) -> str:
        env = os.getenv("ENVIRONMENT", "development")
        if env == "production" and not v:
            raise ValueError("TAVILY_API_KEY is required in production")
        return v


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    ENVIRONMENT: Literal["development", "testing", "production"] = "development"
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    DEBUG: bool = Field(default=False)
    PROJECT_NAME: str = "AI Deep Research Agent"
    VERSION: str = "1.0.0"

    llm: LLMSettings = Field(default_factory=LLMSettings)
    redis_config: RedisSettings = Field(default_factory=RedisSettings)
    qdrant: QdrantSettings = Field(default_factory=QdrantSettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)
    tavily: TavilySettings = Field(default_factory=TavilySettings)

    ENABLE_KNOWLEDGE_GRAPH: bool = False
    SKIP_EVALUATION: bool = True
    MAX_SEARCH_SUBQUERIES: int = 2
    MAX_EXTRACTION_URLS: int = 3
    MAX_KG_CHUNKS: int = 2
    RETRIEVAL_CHUNK_LIMIT: int = 5
    RERANK_TOP_K: int = 4
    MAX_CONTEXT_CHARS: int = 12000

    @model_validator(mode="after")
    def validate_environment_settings(self) -> "Settings":
        if self.ENVIRONMENT == "production":
            if not self.tavily.TAVILY_API_KEY:
                raise ValueError("TAVILY_API_KEY is required in production environment")
            if not self.llm.GROQ_API_KEY and not self.llm.OPENAI_API_KEY:
                raise ValueError("At least one LLM API key is required in production")
            if not self.security.JWT_SECRET_KEY:
                raise ValueError("JWT_SECRET_KEY is required in production")
        return self

    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT == "development"

    @property
    def is_testing(self) -> bool:
        return self.ENVIRONMENT == "testing"

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @property
    def QDRANT_HOST(self) -> str:
        return self.qdrant.QDRANT_HOST

    @property
    def QDRANT_PORT(self) -> int:
        return self.qdrant.QDRANT_PORT

    @property
    def RATE_LIMIT_REQUESTS(self) -> int:
        return self.security.RATE_LIMIT_REQUESTS

    @property
    def RATE_LIMIT_WINDOW_SECS(self) -> int:
        return self.security.RATE_LIMIT_WINDOW_SECS

    @property
    def REDIS_HOST(self) -> str:
        return self.redis_config.REDIS_HOST

    @property
    def REDIS_PORT(self) -> int:
        return self.redis_config.REDIS_PORT


settings = Settings()
