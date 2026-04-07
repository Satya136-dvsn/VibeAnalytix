"""
Application configuration via environment variables using pydantic-settings.
All settings are validated and typed at startup.
"""

from typing import Literal, Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    database_url: str = "postgresql+asyncpg://postgres:password@postgres:5432/vibeanalytix_db"

    # Redis
    redis_url: str = "redis://redis:6379/0"

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    debug: bool = False
    enable_api_docs: bool = True
    enforce_https: bool = False
    cors_allowed_origins: str = "http://localhost:3000"
    trusted_hosts: str = "localhost,127.0.0.1"
    trusted_proxy_ips: str = "127.0.0.1,::1"

    # JWT
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24

    # OpenAI
    openai_api_key: Optional[str] = None
    
    # Gemini
    gemini_api_key: Optional[str] = None
    gemini_text_model: str = "gemini-2.0-flash"

    # File size limits (MB)
    max_repo_size_mb: int = 500
    max_zip_size_mb: int = 100

    # Celery
    celery_broker_url: str = "redis://redis:6379/0"
    celery_result_backend: str = "redis://redis:6379/0"

    # Application
    rate_limit_jobs_per_hour: int = 10
    rate_limit_login_per_minute: int = 20
    rate_limit_register_per_hour: int = 5
    rate_limit_chat_per_minute: int = 30
    cleanup_timeout_minutes: int = 30
    cleanup_sla_minutes: int = 10
    watchdog_interval_minutes: int = 5

    # Logging
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    class Config:
        """Pydantic config for loading from .env file."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()


def parse_csv_setting(value: str) -> list[str]:
    """Parse comma-separated settings into a normalized list."""
    return [item.strip() for item in value.split(",") if item.strip()]
