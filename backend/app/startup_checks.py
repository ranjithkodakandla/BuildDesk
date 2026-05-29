"""
Production startup diagnostics (Phase 16).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List

from app.config import Settings


@dataclass
class StartupCheck:
    name: str
    ok: bool
    level: str  # info | warn | error
    detail: str


def run_startup_checks(settings: Settings) -> List[StartupCheck]:
    checks: List[StartupCheck] = []

    if settings.is_production:
        if settings.jwt_secret_is_default:
            checks.append(StartupCheck(
                "jwt_secret",
                False,
                "error",
                "JWT_SECRET_KEY must be set in production (not the default placeholder).",
            ))
        else:
            checks.append(StartupCheck("jwt_secret", True, "info", "JWT secret configured."))

        if settings.use_local_storage:
            checks.append(StartupCheck(
                "artifact_storage",
                True,
                "warn",
                "USE_LOCAL_STORAGE=true — PDFs are ephemeral on container disk.",
            ))
        elif not settings.storage_bucket or settings.storage_bucket == "builddesk-artifacts-local":
            checks.append(StartupCheck(
                "storage_bucket",
                False,
                "error",
                "STORAGE_BUCKET must be set when USE_LOCAL_STORAGE=false.",
            ))
        else:
            checks.append(StartupCheck(
                "artifact_storage",
                True,
                "info",
                f"GCS mode bucket={settings.storage_bucket}",
            ))

        origins = settings.cors_origins
        localhost_only = origins and all(
            "localhost" in o or "127.0.0.1" in o for o in origins
        )
        if localhost_only:
            checks.append(StartupCheck(
                "cors_origins",
                True,
                "warn",
                "ALLOWED_ORIGINS is localhost-only — browser clients on other hosts will fail CORS.",
            ))
        elif not origins:
            checks.append(StartupCheck(
                "cors_origins",
                False,
                "error",
                "ALLOWED_ORIGINS is empty in production.",
            ))
        else:
            checks.append(StartupCheck(
                "cors_origins",
                True,
                "info",
                f"CORS origins: {', '.join(origins)}",
            ))
    else:
        checks.append(StartupCheck(
            "environment",
            True,
            "info",
            f"app_env={settings.app_env} storage={settings.artifact_storage_mode}",
        ))

    return checks


def log_startup_checks(checks: List[StartupCheck]) -> None:
    for check in checks:
        prefix = {"info": "✓", "warn": "⚠", "error": "✗"}[check.level]
        print(f"{prefix} [{check.name}] {check.detail}")


def has_blocking_errors(checks: List[StartupCheck]) -> bool:
    return any(c.level == "error" and not c.ok for c in checks)
