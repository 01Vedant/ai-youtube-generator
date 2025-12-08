from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/shares", tags=["shares"])


class ShareCreate(BaseModel):
    artifact_id: str
    visibility: str = "unlisted"  # "unlisted" | "private" | "public"


class ShareOut(BaseModel):
    share_id: str
    url: str


@router.post("", response_model=ShareOut)
def create_share(payload: ShareCreate) -> ShareOut:
    if not payload.artifact_id:
        raise HTTPException(status_code=400, detail="artifact_id required")
    share_id = f"shr_{payload.artifact_id}"
    return ShareOut(share_id=share_id, url=f"https://example.com/shares/{share_id}")
