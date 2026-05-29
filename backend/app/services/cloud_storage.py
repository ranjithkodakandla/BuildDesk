"""
Cloud Storage Service (Phase 7, production GCS in Phase 16).

Local/mock mode writes under backend/artifacts/mock_gcs/.
GCS mode uses Application Default Credentials (Cloud Run service account).
"""
from __future__ import annotations

import logging
import os
import uuid
from datetime import timedelta
from typing import Optional, Tuple

from app.config import Settings, get_settings

logger = logging.getLogger(__name__)

LOCAL_STORAGE_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "artifacts", "mock_gcs"
)


def parse_gs_uri(storage_reference: str) -> Tuple[str, str]:
    """Return (bucket, object_name) from gs://bucket/path/to/object."""
    if not storage_reference.startswith("gs://"):
        raise ValueError(f"Not a GCS URI: {storage_reference}")
    remainder = storage_reference[5:]
    bucket, _, object_name = remainder.partition("/")
    if not bucket or not object_name:
        raise ValueError(f"Invalid GCS URI: {storage_reference}")
    return bucket, object_name


class CloudStorageService:
    def __init__(self, settings: Optional[Settings] = None) -> None:
        self._settings = settings or get_settings()
        self._use_local = self._settings.use_local_storage
        self._bucket = self._settings.storage_bucket
        self._gcs_client = None

        if self._use_local:
            os.makedirs(LOCAL_STORAGE_DIR, exist_ok=True)

    @property
    def mode(self) -> str:
        return "local" if self._use_local else "gcs"

    def _get_gcs_client(self):
        if self._gcs_client is None:
            from google.cloud import storage

            project = self._settings.gcp_project_id or None
            self._gcs_client = storage.Client(project=project)
        return self._gcs_client

    def _package_object_name(self, project_id: uuid.UUID, package_id: uuid.UUID) -> str:
        return f"projects/{project_id}/packages/{package_id}.pdf"

    def upload_pdf(
        self, project_id: uuid.UUID, package_id: uuid.UUID, pdf_bytes: bytes
    ) -> str:
        """Upload package PDF; returns storage reference URI."""
        object_name = self._package_object_name(project_id, package_id)
        return self.upload_bytes(
            object_name,
            pdf_bytes,
            content_type="application/pdf",
        )

    def upload_bytes(
        self,
        object_name: str,
        data: bytes,
        content_type: str = "application/octet-stream",
    ) -> str:
        if not data:
            raise ValueError("Cannot upload empty payload.")

        if self._use_local:
            safe_name = object_name.replace("/", "_")
            file_path = os.path.join(LOCAL_STORAGE_DIR, safe_name)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, "wb") as f:
                f.write(data)
            return f"local://{file_path}"

        client = self._get_gcs_client()
        bucket = client.bucket(self._bucket)
        blob = bucket.blob(object_name)
        blob.upload_from_string(data, content_type=content_type)
        ref = f"gs://{self._bucket}/{object_name}"
        logger.info("Uploaded %s bytes to %s", len(data), ref)
        return ref

    def exists(self, storage_reference: str) -> bool:
        if not storage_reference:
            return False
        if storage_reference.startswith("local://"):
            return os.path.isfile(storage_reference.replace("local://", "", 1))
        if storage_reference.startswith("gs://"):
            try:
                bucket_name, object_name = parse_gs_uri(storage_reference)
                client = self._get_gcs_client()
                return client.bucket(bucket_name).blob(object_name).exists()
            except Exception as exc:
                logger.warning("GCS exists check failed for %s: %s", storage_reference, exc)
                return False
        return os.path.exists(storage_reference)

    def download_bytes(self, storage_reference: str) -> bytes:
        if storage_reference.startswith("local://"):
            path = storage_reference.replace("local://", "", 1)
            with open(path, "rb") as f:
                return f.read()

        if storage_reference.startswith("gs://"):
            bucket_name, object_name = parse_gs_uri(storage_reference)
            client = self._get_gcs_client()
            blob = client.bucket(bucket_name).blob(object_name)
            if not blob.exists():
                raise FileNotFoundError(f"GCS object not found: {storage_reference}")
            return blob.download_as_bytes()

        with open(storage_reference, "rb") as f:
            return f.read()

    def get_download_url(self, storage_reference: str) -> Optional[str]:
        """
        Local mode: filesystem path for FileResponse.
        GCS mode: V4 signed HTTPS URL for browser/API redirect.
        """
        if not storage_reference:
            return None

        if storage_reference.startswith("local://"):
            return storage_reference.replace("local://", "", 1)

        if storage_reference.startswith("gs://"):
            bucket_name, object_name = parse_gs_uri(storage_reference)
            client = self._get_gcs_client()
            blob = client.bucket(bucket_name).blob(object_name)
            ttl = self._settings.gcs_signed_url_ttl_seconds
            return blob.generate_signed_url(
                version="v4",
                expiration=timedelta(seconds=ttl),
                method="GET",
            )

        return storage_reference
