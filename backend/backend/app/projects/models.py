from __future__ import annotations
from pydantic import BaseModel
from typing import Optional, List


class Project(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    cover_thumb: Optional[str] = None
    created_at: str
    video_count: Optional[int] = None


class ProjectCreate(BaseModel):
    title: str
    description: Optional[str] = None


class ProjectUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    cover_thumb: Optional[str] = None


class ProjectList(BaseModel):
    projects: List[Project]
