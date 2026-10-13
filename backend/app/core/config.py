"""Application configuration settings.

Contract Version: 3.0.0
Single Source of Truth: docs/ARCHITECTURE_API_CONTRACT.md, Sections 17, 21
"""

import json
from typing import Any

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime application settings for ThreatLens v3."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    SERVICE_NAME: str = "threatlens-api"
    API_V1_PREFIX: str = "/api/v1"
    VERSION: str = "3.0.0"
    CONTRACT_VERSION: str = "3.0.0"
    SCORING_VERSION: str = "3.0.0"

    # Database
    DATABASE_URL: str = "sqlite:///./threatlens.db"

    # CORS
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "https://threatlens-ui.onrender.com",
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Any) -> list[str]:
        if isinstance(v, str):
            if v.startswith("[") and v.endswith("]"):
                origins = json.loads(v)
            else:
                origins = [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            origins = list(v)
        else:
            origins = ["http://localhost:5173"]

        render_origin = "https://threatlens-ui.onrender.com"
        if render_origin not in origins:
            origins.append(render_origin)
        return origins

    # Providers
    APPLE_COUNTRY: str = "in"
    CACHE_TTL_SECONDS: int = 3600
    SCAN_TIMEOUT_SECONDS: int = 90

    # Optional P1 settings
    LLM_API_KEY: str | None = None
    LLM_MODEL: str | None = None
    BLUESKY_APP_PASSWORD: str | None = None
    BLUESKY_HANDLE: str | None = None
    SERPER_API_KEY: str | None = None
    BRAVE_API_KEY: str | None = None


settings = Settings()
