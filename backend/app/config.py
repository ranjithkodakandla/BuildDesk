"""
Application Settings
====================
Centralised, environment-variable-driven configuration.

Uses pydantic-settings so every value can be overridden via:
  • .env file (local development)
  • OS environment (Cloud Run / CI)
  • Secret Manager projected env-vars (production)
"""

from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All tuneable application settings."""

    # Application
    app_env: str = "development"
    app_version: str = "0.1.0"

    # CORS – comma-separated list handled as a list by pydantic-settings
    allowed_origins: List[str] = ["http://localhost:5173"]

    # Database (Phase 2)
    database_url: str = ""

    # GCP (Phase 2 / 3)
    gcp_project_id: str = ""
    gcp_region: str = "us-central1"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    """Return a cached singleton Settings instance."""
    return Settings()
