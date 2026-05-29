"""
Cloud Storage Service (Phase 7)
Handles saving PDF artifacts to persistent storage.
For local development, it saves to a local mock directory.
In production, it would upload to Google Cloud Storage (GCS).
"""
import os
import uuid
from typing import Optional

# Determine if we are in local fallback mode
USE_LOCAL_STORAGE = os.getenv("USE_LOCAL_STORAGE", "True").lower() in ("true", "1", "yes")
STORAGE_BUCKET = os.getenv("STORAGE_BUCKET", "builddesk-artifacts-local")
LOCAL_STORAGE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "artifacts", "mock_gcs")

class CloudStorageService:
    def __init__(self):
        if USE_LOCAL_STORAGE:
            os.makedirs(LOCAL_STORAGE_DIR, exist_ok=True)

    def upload_pdf(self, project_id: uuid.UUID, package_id: uuid.UUID, pdf_bytes: bytes) -> str:
        """
        Uploads a PDF package to storage and returns the storage reference URI.
        """
        object_name = f"projects/{project_id}/packages/{package_id}.pdf"
        
        if USE_LOCAL_STORAGE:
            # Mock GCS upload by writing to local artifacts folder
            safe_name = str(package_id) + ".pdf"
            file_path = os.path.join(LOCAL_STORAGE_DIR, safe_name)
            with open(file_path, "wb") as f:
                f.write(pdf_bytes)
            # Return a mocked URI that can be used to retrieve it later
            return f"local://{file_path}"
        else:
            # Placeholder for actual google-cloud-storage logic
            # client = storage.Client()
            # bucket = client.bucket(STORAGE_BUCKET)
            # blob = bucket.blob(object_name)
            # blob.upload_from_string(pdf_bytes, content_type="application/pdf")
            return f"gs://{STORAGE_BUCKET}/{object_name}"

    def get_download_url(self, storage_reference: str) -> Optional[str]:
        """
        Returns a signed URL or local path for downloading the artifact.
        """
        if not storage_reference:
            return None
            
        if storage_reference.startswith("local://"):
            return storage_reference.replace("local://", "")
            
        if storage_reference.startswith("gs://"):
            # Placeholder for signed URL generation
            # client = storage.Client()
            # blob = Blob.from_string(storage_reference, client=client)
            # return blob.generate_signed_url(expiration=timedelta(hours=1))
            return storage_reference
            
        return storage_reference
