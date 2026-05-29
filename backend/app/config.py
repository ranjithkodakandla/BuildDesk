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
    debug: bool = False

    # CORS – comma-separated origins (env: ALLOWED_ORIGINS)
    allowed_origins: str = "http://localhost:5173"

    # Database
    database_url: str = "sqlite:///./builddesk.db"
    use_sql_repository: bool = False

    # JWT Authentication
    jwt_secret_key: str = "CHANGE-ME-IN-PRODUCTION-use-openssl-rand-hex-32"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # Artifact storage (Phase 16)
    use_local_storage: bool = True
    storage_bucket: str = "builddesk-artifacts-local"
    gcs_signed_url_ttl_seconds: int = 3600

    # GCP
    gcp_project_id: str = ""
    gcp_region: str = "us-central1"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    @property
    def cors_origins(self) -> List[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def jwt_secret_is_default(self) -> bool:
        return self.jwt_secret_key == "CHANGE-ME-IN-PRODUCTION-use-openssl-rand-hex-32"

    @property
    def artifact_storage_mode(self) -> str:
        return "local" if self.use_local_storage else "gcs"


@lru_cache
def get_settings() -> Settings:
    """Return a cached singleton Settings instance."""
    return Settings()
