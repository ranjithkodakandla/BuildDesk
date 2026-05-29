"""Phase 16 — CloudStorageService local mode and GCS URI helpers."""
from __future__ import annotations

import os
import uuid
from unittest.mock import MagicMock, patch

import pytest

from app.config import Settings
from app.services.cloud_storage import LOCAL_STORAGE_DIR, CloudStorageService, parse_gs_uri


@pytest.fixture
def local_settings(tmp_path, monkeypatch):
    monkeypatch.setenv("USE_LOCAL_STORAGE", "true")
    monkeypatch.setenv("STORAGE_BUCKET", "test-bucket")
    from app.config import get_settings

    get_settings.cache_clear()
    settings = get_settings()
    yield settings
    get_settings.cache_clear()


def test_parse_gs_uri():
    bucket, obj = parse_gs_uri("gs://my-bucket/projects/p1/packages/x.pdf")
    assert bucket == "my-bucket"
    assert obj == "projects/p1/packages/x.pdf"


def test_local_upload_download_exists(local_settings):
    svc = CloudStorageService(settings=Settings(use_local_storage=True))
    project_id = uuid.uuid4()
    package_id = uuid.uuid4()
    payload = b"%PDF-1.4 test"

    ref = svc.upload_pdf(project_id, package_id, payload)
    assert ref.startswith("local://")
    assert svc.exists(ref)
    assert svc.download_bytes(ref) == payload
    path = svc.get_download_url(ref)
    assert path and os.path.isfile(path)


def test_upload_bytes_rejects_empty(local_settings):
    svc = CloudStorageService(settings=Settings(use_local_storage=True))
    with pytest.raises(ValueError, match="empty"):
        svc.upload_bytes("projects/x/file.csv", b"", content_type="text/csv")


@patch("google.cloud.storage.Client")
def test_gcs_upload_and_signed_url(mock_client_cls):
    mock_blob = MagicMock()
    mock_blob.exists.return_value = True
    mock_blob.download_as_bytes.return_value = b"%PDF-gcs"
    mock_blob.generate_signed_url.return_value = "https://storage.googleapis.com/signed"

    mock_bucket = MagicMock()
    mock_bucket.blob.return_value = mock_blob
    mock_client = MagicMock()
    mock_client.bucket.return_value = mock_bucket
    mock_client_cls.return_value = mock_client

    settings = Settings(
        use_local_storage=False,
        storage_bucket="prod-artifacts",
        gcp_project_id="stonedesk-app",
    )
    svc = CloudStorageService(settings=settings)
    pid, pkg = uuid.uuid4(), uuid.uuid4()
    ref = svc.upload_pdf(pid, pkg, b"%PDF-gcs")

    assert ref == f"gs://prod-artifacts/projects/{pid}/packages/{pkg}.pdf"
    mock_blob.upload_from_string.assert_called_once()
    assert svc.exists(ref)
    assert svc.download_bytes(ref) == b"%PDF-gcs"
    url = svc.get_download_url(ref)
    assert url == "https://storage.googleapis.com/signed"
    mock_blob.generate_signed_url.assert_called_once()


def test_startup_checks_production_gcs_bucket():
    from app.startup_checks import run_startup_checks

    settings = Settings(
        app_env="production",
        jwt_secret_key="real-secret",
        use_local_storage=False,
        storage_bucket="",
        allowed_origins="https://app.example.com",
    )
    checks = run_startup_checks(settings)
    assert any(c.name == "storage_bucket" and not c.ok for c in checks)
