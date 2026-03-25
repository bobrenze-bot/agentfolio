"""
Core configuration for AgentRank backend.
"""

import os
from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    # App
    APP_NAME: str = "AgentRank"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = ENVIRONMENT == "development"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")

    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://agentrank:agentrank_dev_password@localhost:5432/agentrank",
    )

    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")

    # CORS
    ALLOWED_HOSTS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8000",
        "http://localhost:5173",  # Vite default
    ]

    # External APIs
    PAPERCLIP_API_URL: str = os.getenv("PAPERCLIP_API_URL", "http://localhost:3100")
    PAPERCLIP_API_KEY: str = os.getenv("PAPERCLIP_API_KEY", "")
    PAPERCLIP_WEBHOOK_SECRET: str = os.getenv("PAPERCLIP_WEBHOOK_SECRET", "")

    LOBSTER_API_KEY: str = os.getenv("LOBSTER_API_KEY", "")

    # Feature flags
    ENABLE_REALTIME: bool = os.getenv("ENABLE_REALTIME", "true").lower() == "true"
    ENABLE_WEBHOOKS: bool = os.getenv("ENABLE_WEBHOOKS", "true").lower() == "true"
    ENABLE_FRAUD_DETECTION: bool = (
        os.getenv("ENABLE_FRAUD_DETECTION", "true").lower() == "true"
    )

    # Scoring
    SCORE_DECAY_HALF_LIFE_DAYS: int = 30
    MIN_TASKS_FOR_SCORE: int = 1

    class Config:
        case_sensitive = True


settings = Settings()
