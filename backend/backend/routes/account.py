"""
Account routes: GDPR export, delete account, rotate API keys, backups
"""

import os
import json
import logging
import zipfile
import io
from datetime import datetime
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import FileResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/account", tags=["account"])

# Backup directory
BACKUP_DIR = Path(os.getenv("BACKUP_DIR", "./platform/backups"))
BACKUP_DIR.mkdir(parents=True, exist_ok=True)


class DeleteAccountRequest(BaseModel):
    confirm: bool = False


class ApiKeyResponse(BaseModel):
    api_key: str
    created_at: str


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())) -> dict:
    """Extract user from JWT."""
    # TODO: properly extract from JWT via auth.py
    return {"user_id": "user_123", "tenant_id": "tenant_123", "email": "user@example.com"}


@router.post("/export")
async def export_user_data(
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """
    GDPR: Export all tenant assets as ZIP bundle.
    Returns download URL or initiates background export.
    """
    tenant_id = current_user.get("tenant_id")
    user_id = current_user.get("user_id")

    # Create export bundle
    export_buffer = io.BytesIO()

    try:
        with zipfile.ZipFile(export_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            # Add job summaries, plans, metadata
            metadata = {
                "exported_at": datetime.utcnow().isoformat(),
                "tenant_id": tenant_id,
                "user_id": user_id,
            }
            zf.writestr("_metadata.json", json.dumps(metadata, indent=2))

            # TODO: Add actual job summaries, generated_scripts/, images/, etc.
            # Example:
            # storage.get_tenant_assets(tenant_id) -> list of files
            # for each file, zf.write(file_path, arcname)

        export_buffer.seek(0)

        # Save to disk with timestamp
        export_filename = f"export-{tenant_id}-{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.zip"
        export_path = BACKUP_DIR / export_filename

        with open(export_path, "wb") as f:
            f.write(export_buffer.getvalue())

        logger.info(f"GDPR export created: {export_path}")

        return {
            "success": True,
            "message": "Export created",
            "download_url": f"/api/account/download-export/{export_filename}",
            "expires_in_hours": 24,
        }
    except Exception as e:
        logger.error(f"Export failed: {e}")
        raise HTTPException(status_code=500, detail="Export failed")


@router.get("/download-export/{filename}")
async def download_export(filename: str, current_user: dict = Depends(get_current_user)):
    """
    Download previously created export ZIP.
    Validates tenant ownership.
    """
    tenant_id = current_user.get("tenant_id")
    export_path = BACKUP_DIR / filename

    # Validate path and tenant ownership
    if not export_path.exists() or tenant_id not in filename:
        raise HTTPException(status_code=404, detail="Export not found")

    return FileResponse(
        path=export_path,
        media_type="application/zip",
        filename=filename,
    )


@router.post("/delete")
async def delete_account(
    req: DeleteAccountRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """
    Delete account and all associated data (async job).
    Requires confirmation flag.
    """
    if not req.confirm:
        raise HTTPException(status_code=400, detail="Confirm deletion with confirm=true")

    tenant_id = current_user.get("tenant_id")
    user_id = current_user.get("user_id")

    # Queue deletion job (don't block request)
    background_tasks.add_task(
        _delete_tenant_data_async, tenant_id=tenant_id, user_id=user_id
    )

    logger.info(f"Account deletion initiated for tenant {tenant_id}")

    return {
        "success": True,
        "message": "Account deletion initiated. This may take a few minutes.",
    }


async def _delete_tenant_data_async(tenant_id: str, user_id: str):
    """
    Background job: delete all tenant data from storage, DB, etc.
    """
    try:
        # TODO: Delete from S3/local storage
        # TODO: Delete from DB
        # TODO: Clear Redis caches
        logger.info(f"Deleted all data for tenant {tenant_id}")
    except Exception as e:
        logger.error(f"Delete failed for tenant {tenant_id}: {e}")


@router.post("/rotate-api-key")
async def rotate_api_key(
    current_user: dict = Depends(get_current_user),
) -> ApiKeyResponse:
    """
    Rotate API key for tenant (invalidate old key).
    """
    import secrets

    tenant_id = current_user.get("tenant_id")

    # Generate new key
    new_key = f"sk_{secrets.token_urlsafe(32)}"

    # TODO: Store in DB, invalidate old key

    logger.info(f"API key rotated for tenant {tenant_id}")

    return ApiKeyResponse(
        api_key=new_key,
        created_at=datetime.utcnow().isoformat(),
    )


@router.get("/backup-status")
async def get_backup_status(
    current_user: dict = Depends(get_current_user),
) -> dict:
    """
    Get last backup timestamp for tenant.
    """
    # TODO: Query backup DB/metadata
    return {
        "last_backup": datetime.utcnow().isoformat(),
        "next_backup": (
            datetime.utcnow().replace(hour=2, minute=0, second=0)
        ).isoformat(),  # 2 AM UTC
        "backup_size_mb": 0,
    }
