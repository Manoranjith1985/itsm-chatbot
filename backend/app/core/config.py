"""Application configuration via pydantic-settings."""
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_ENV: str = "development"
    LOG_LEVEL: str = "INFO"
    MONGODB_URI: str
    JWT_PRIVATE_KEY: str
    JWT_PUBLIC_KEY: str
    JWT_ALGORITHM: str = "RS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    ENCRYPTION_KEY: str
    LITELLM_DEFAULT_MODEL: str = "gpt-4o-mini"
    OPENAI_API_KEY: str = ""
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000"]
    REDIS_URL: str = ""
    RATE_LIMIT_PER_MINUTE: int = 10
    MAX_INPUT_CHARS: int = 4000
    CONVERSATION_CONTEXT_TURNS: int = 6
    AI_WRITE_OPERATIONS: bool = False
    SLACK_SIGNING_SECRET: str = ""
    SLACK_BOT_TOKEN: str = ""
    TEAMS_APP_ID: str = ""
    TEAMS_APP_SECRET: str = ""
    GCHAT_WEBHOOK_SECRET: str = ""


settings = Settings()
