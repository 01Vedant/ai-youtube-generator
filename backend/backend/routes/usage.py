from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException

from app.auth.security import get_current_user
from app.usage.models import UsageToday
from app.usage.service import (
    get_usage,
    get_limits,
    reset_at_utc,
    day_utc,
    range_days,
    get_usage_range,
)

router = APIRouter()


@router.get("/today", response_model=UsageToday)
def get_usage_today(user=Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    u = get_usage(user["id"])  # { user_id, day, renders, tts_sec }
    limits = get_limits(user["id"])       # { renders_per_day, tts_sec_per_day }
    reset_at = reset_at_utc(u["day"])  # next day 00:00:00Z
    return UsageToday(
        day=u["day"],
        renders=int(u["renders"]),
        tts_sec=int(u["tts_sec"]),
        limit_renders=int(limits["renders_per_day"]),
        limit_tts_sec=int(limits["tts_sec_per_day"]),
        reset_at=reset_at,
    )


@router.get("/history")
def get_usage_history(days: int = 14, user=Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    if days not in (14, 30, 90):
        days = 14
    end = day_utc()
    start, end = range_days(end, days)
    series = get_usage_range(user["id"], start, end)
    return {"days": days, "series": series}
