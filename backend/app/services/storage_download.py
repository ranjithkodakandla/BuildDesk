"""HTTP responses for artifact storage references (local or GCS)."""
from __future__ import annotations

import os

from fastapi import HTTPException
from fastapi.responses import FileResponse, Response

from app.services.cloud_storage import CloudStorageService


def artifact_file_response(
    storage_reference: str,
    *,
    filename: str,
    media_type: str = "application/octet-stream",
    inline: bool = True,
) -> Response:
    """
    Return artifact bytes to the client.

    Local files use FileResponse. GCS objects are proxied through the API
    (service account credentials) so Cloud Run does not require signed-URL keys.
    """
    if not storage_reference:
        raise HTTPException(status_code=404, detail="No storage reference.")

    svc = CloudStorageService()
    disposition = "inline" if inline else "attachment"

    if storage_reference.startswith("local://"):
        path = storage_reference.replace("local://", "", 1)
        if not os.path.isfile(path):
            raise HTTPException(status_code=404, detail="Artifact file not found.")
        return FileResponse(
            path=path,
            media_type=media_type,
            filename=filename,
            content_disposition_type=disposition,
        )

    if storage_reference.startswith("gs://"):
        if not svc.exists(storage_reference):
            raise HTTPException(status_code=404, detail="Artifact not found in object storage.")
        try:
            data = svc.download_bytes(storage_reference)
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail="Artifact not found in object storage.")
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to read artifact from storage: {exc}",
            ) from exc
        return Response(
            content=data,
            media_type=media_type,
            headers={
                "Content-Disposition": f'{disposition}; filename="{filename}"',
            },
        )

    if os.path.isfile(storage_reference):
        return FileResponse(
            path=storage_reference,
            media_type=media_type,
            filename=filename,
            content_disposition_type=disposition,
        )

    raise HTTPException(status_code=404, detail="Unsupported storage reference.")
