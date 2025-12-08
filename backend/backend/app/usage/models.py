from __future__ import annotations
from pydantic import BaseModel


class UsageToday(BaseModel):
    day: str            # YYYY-MM-DD
    renders: int
    tts_sec: int
    limit_renders: int
    limit_tts_sec: int
    reset_at: str       # ISO UTC
