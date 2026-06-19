"""Configuration management for FootyOracle."""

from typing import Literal
from functools import lru_cache
from pydantic import Field, validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings from environment variables."""
    
    # Telegram
    BOT_TOKEN: str = Field(..., description="Telegram bot API token")
    CHAT_ID: str = Field(..., description="Telegram chat ID for publishing")
    
    # Database
    DATABASE_URL: str = Field(..., description="SQLAlchemy database URL")
    
    # Scheduler
    POST_HOUR: int = Field(default=8, ge=0, le=23, description="Hour to publish daily picks (0-23)")
    TIMEZONE: str = Field(default="Africa/Lagos", description="Timezone for scheduling")
    
    # Scoring
    MIN_SCORE: int = Field(default=75, ge=0, le=100, description="Minimum confidence score to publish")
    MAX_DAILY_PICKS: int = Field(default=5, ge=1, description="Maximum picks to publish daily")
    
    # API
    API_HOST: str = Field(default="0.0.0.0", description="API host to bind to")
    API_PORT: int = Field(default=8000, ge=1, le=65535, description="API port")
    
    # Logging
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(
        default="INFO", 
        description="Logging level"
    )
    
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore"
    )
    
    @validator("BOT_TOKEN")
    def validate_bot_token(cls, v):
        if not v or len(v) < 10:
            raise ValueError("BOT_TOKEN must be set and valid")
        return v
    
    @validator("DATABASE_URL")
    def validate_database_url(cls, v):
        if not v or not any(v.startswith(prefix) for prefix in ["postgresql://", "sqlite://", "mysql://", "postgres://"]):
            raise ValueError("DATABASE_URL must be a valid database connection string")
        return v


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
