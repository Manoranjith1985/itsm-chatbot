from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
from typing import List


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    MONGODB_URI: str = "mongodb://localhost:27017"

    # JWT
    JWT_PRIVATE_KEY: str = ""
    JWT_PUBLIC_KEY: str = ""
    JWT_ALGORITHM: str = "RS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # Encryption
    ENCRYPTION_KEY: str = ""

    # LLM
    LITELLM_DEFAULT_MODEL: str = "gpt-4o-mini"
    OPENAI_API_KEY: str = ""

    # CORS — includes GitHub Pages frontend by default
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8080",
        "https://manoranjith1985.github.io",
    ]

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_origins(cls, v):
        """Accept either a list or a comma-separated string from env vars."""
        if isinstance(v, str):
            return [o.strip() for o in v.split(",") if o.strip()]
        return v

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Feature flags
    AI_WRITE_OPERATIONS: bool = False

    # App
    APP_ENV: str = "development"
    LOG_LEVEL: str = "INFO"
    RATE_LIMIT_PER_MINUTE: int = 10
    MAX_INPUT_CHARS: int = 4000
    CONVERSATION_CONTEXT_TURNS: int = 6


settings = Settings()
