from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

from fastapi import HTTPException, status

from app.db import get_conn
from app.plans.entitlements import get_plan_spec


def day_utc(dt: Optional[datetime] = None) -> str:
    d = (dt or datetime.now(timezone.utc)).date()
    return d.isoformat()


def shift_days(day_str: str, n: int) -> str:
    base = datetime.strptime(day_str, "%Y-%m-%d").date()
    return (base + timedelta(days=n)).isoformat()


def range_days(end_day: str, days: int) -> Tuple[str, str]:
    # days is the window size; end_day inclusive
    start = shift_days(end_day, -(days - 1))
    return start, end_day


def get_usage_range(user_id: str, start_day: str, end_day: str) -> List[Dict]:
    """Return gap-filled daily usage rows within [start_day, end_day].

    Each item: { day: YYYY-MM-DD, renders: int, tts_sec: int }
    Missing days are filled with zeros.
    """
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
        """
        SELECT day, COALESCE(renders, 0) as renders, COALESCE(tts_sec, 0) as tts_sec
        FROM usage_daily
        WHERE user_id = ? AND day BETWEEN ? AND ?
        ORDER BY day ASC
        """,
        (user_id, start_day, end_day),
    )
        rows = cur.fetchall()
        by_day: Dict[str, Dict] = {r[0]: {"day": r[0], "renders": int(r[1]), "tts_sec": int(r[2])} for r in rows}

    # Build the full range
        start = datetime.strptime(start_day, "%Y-%m-%d").date()
        end = datetime.strptime(end_day, "%Y-%m-%d").date()
        out: List[Dict] = []
        cur_day = start
        while cur_day <= end:
            key = cur_day.isoformat()
            out.append(by_day.get(key, {"day": key, "renders": 0, "tts_sec": 0}))
            cur_day = cur_day + timedelta(days=1)
        return out
    finally:
        conn.close()


def today_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def reset_at_utc(day_str: str) -> str:
    # day_str is YYYY-MM-DD (UTC); next day at 00:00:00Z
    day = datetime.strptime(day_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    next_day = day + timedelta(days=1)
    return next_day.strftime("%Y-%m-%dT00:00:00Z")


def _get_plan_id_for_user(user_id: str) -> str:
    try:
        conn = get_conn()
        try:
            row = conn.execute("SELECT plan_id FROM users WHERE id = ?", (user_id,)).fetchone()
        finally:
            conn.close()
        if row and row["plan_id"]:
            return str(row["plan_id"]) or "free"
    except Exception:
        pass
    return "free"


def get_limits(user_id: str | None = None) -> dict:
    if user_id:
        plan_id = _get_plan_id_for_user(user_id)
        spec = get_plan_spec(plan_id)
        return {
            "renders_per_day": int(spec["quotas"].get("renders_per_day", 10)),
            "tts_sec_per_day": int(spec["quotas"].get("tts_sec_per_day", 900)),
        }
    # Fallback to env-based defaults for anonymous
    renders = int(os.getenv("QUOTA_RENDERS_PER_DAY", "10"))
    tts_sec = int(os.getenv("QUOTA_TTS_SEC_PER_DAY", "900"))
    return {"renders_per_day": renders, "tts_sec_per_day": tts_sec}


def _ensure_row(user_id: str, day: str) -> None:
    conn = get_conn()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO usage_daily (user_id, day, renders, tts_sec) VALUES (?,?,0,0)",
            (user_id, day),
        )
        conn.commit()
    finally:
        conn.close()


def get_usage(user_id: str) -> dict:
    day = today_str()
    _ensure_row(user_id, day)
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT user_id, day, renders, tts_sec FROM usage_daily WHERE user_id = ? AND day = ?",
            (user_id, day),
        ).fetchone()
        if not row:
            return {"user_id": user_id, "day": day, "renders": 0, "tts_sec": 0}
        return dict(row)
    finally:
        conn.close()


def inc_renders(user_id: str, n: int = 1) -> None:
    day = today_str()
    _ensure_row(user_id, day)
    conn = get_conn()
    try:
        conn.execute(
            "UPDATE usage_daily SET renders = renders + ? WHERE user_id = ? AND day = ?",
            (n, user_id, day),
        )
        conn.commit()
    finally:
        conn.close()


def inc_tts_sec(user_id: str, seconds: int) -> None:
    day = today_str()
    _ensure_row(user_id, day)
    conn = get_conn()
    try:
        conn.execute(
            "UPDATE usage_daily SET tts_sec = tts_sec + ? WHERE user_id = ? AND day = ?",
            (int(seconds), user_id, day),
        )
        conn.commit()
    finally:
        conn.close()


def check_quota_or_raise(user_id: str, *, add_renders: int = 0, add_tts_sec: int = 0) -> None:
    usage = get_usage(user_id)
    limits = get_limits(user_id)
    day = usage["day"]

    # Renders
    if add_renders:
        new_total = usage["renders"] + int(add_renders)
        if new_total > limits["renders_per_day"]:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": {
                        "code": "QUOTA_EXCEEDED",
                        "metric": "renders",
                        "limit": limits["renders_per_day"],
                        "used": usage["renders"],
                        "reset_at": reset_at_utc(day),
                    }
                },
            )

    # TTS seconds
    if add_tts_sec:
        new_total = usage["tts_sec"] + int(add_tts_sec)
        if new_total > limits["tts_sec_per_day"]:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": {
                        "code": "QUOTA_EXCEEDED",
                        "metric": "tts_sec",
                        "limit": limits["tts_sec_per_day"],
                        "used": usage["tts_sec"],
                        "reset_at": reset_at_utc(day),
                    }
                },
            )
