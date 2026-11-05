from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    DATABASE_URL: str
    STORY_PROVIDER: Literal["deepseek", "gemini"] = "deepseek"
    DEEPSEEK_API_KEY: SecretStr | None = None
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    DEEPSEEK_MODEL: str = "deepseek/deepseek-v4.1-flash"
    DEEPSEEK_TIMEOUT_SECONDS: float = Field(default=120, gt=0)
    DEEPSEEK_MAX_TOKENS: int = Field(default=8192, ge=1, le=393216)
    GEMINI_API_KEY: SecretStr | None = None
    GEMINI_BASE_URL: str = "https://generativelanguage.googleapis.com/v1beta"
    GEMINI_MODEL: str = "gemini-2.5-flash"
    GEMINI_TIMEOUT_SECONDS: float = Field(default=120, gt=0)
    GEMINI_MAX_TOKENS: int = Field(default=8192, ge=1, le=65536)

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[2] / ".env",
        env_file_encoding="utf-8",
        extra="ignore",  # The shared .env also contains Docker Compose settings.
        hide_input_in_errors=True,
    )


@lru_cache
def get_settings() -> Settings:
    """Load configuration at the composition boundary, never on model import."""
    return Settings()
