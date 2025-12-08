"""
Library API models
Pydantic schemas for library endpoints
"""

from typing import List, Literal, Optional
from pydantic import BaseModel, Field


class LibraryItem(BaseModel):
    """Single library entry with standardized schema."""
    id: str = Field(..., description="Job ID")
    title: str = Field(..., description="Video topic/title")
    created_at: str = Field(..., description="ISO timestamp")
    duration_sec: Optional[float] = Field(None, description="Video duration in seconds")
    voice: Optional[Literal["Swara", "Diya"]] = Field(None, description="Hindi TTS voice used")
    template: Optional[str] = Field(None, description="Template name if used")
    state: str = Field(..., description="Job state: completed, error, running, etc")
    thumbnail_url: Optional[str] = Field(None, description="Thumbnail URL")
    video_url: Optional[str] = Field(None, description="Final video URL")
    error: Optional[str] = Field(None, description="Error message if failed")


class FetchLibraryResponse(BaseModel):
    """Paginated library response with metadata."""
    entries: List[LibraryItem] = Field(..., description="Library items for current page")
    total: int = Field(..., description="Total number of items across all pages")
    page: int = Field(..., description="Current page number (1-indexed)")
    pageSize: int = Field(..., description="Number of items per page")
    
    class Config:
        json_schema_extra = {
            "example": {
                "entries": [
                    {
                        "id": "abc-123",
                        "title": "Sanatan Dharma Principles",
                        "created_at": "2025-12-05T10:30:00Z",
                        "duration_sec": 45.5,
                        "voice": "Swara",
                        "template": "devotional",
                        "state": "completed",
                        "thumbnail_url": "/artifacts/abc-123/thumbnail.jpg",
                        "video_url": "/artifacts/abc-123/final/final.mp4",
                        "error": None
                    }
                ],
                "total": 42,
                "page": 1,
                "pageSize": 20
            }
        }
