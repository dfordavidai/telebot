"""Configuration management for FootyOracle."""

from typing import Literal
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings from environment variables."""
    
    # Telegram
    BOT_TOKEN: str
    CHAT_ID: str
    
    # Database
    DATABASE_URL: str
    
    # Scheduler
    POST_HOUR: int = 8
    TIMEZONE: str = "Africa/Lagos"
    
    # Scoring
    MIN_SCORE: int = 75
    MAX_DAILY_PICKS: int = 5
    
    # API
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    
    # Logging
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
