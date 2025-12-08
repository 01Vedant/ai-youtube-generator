from __future__ import annotations

from pydantic import BaseModel


class ShareCreate(BaseModel):
    job_id: str


class ShareInfo(BaseModel):
    share_id: str
    job_id: str
    created_at: str
    revoked: bool
