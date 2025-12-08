import hashlib
from app.db import get_conn, _utcnow_iso
import os

GOAL_DEFAULT = int(os.getenv('GROWTH_SHARE_GOAL', '3'))


def hash_ip(ip: str, ua: str | None) -> str:
    ua_pfx = (ua or '')[:24]
    raw = f"{ip}|{ua_pfx}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def record_share_hit(share_id: str, ip: str, ua: str | None) -> None:
    ip_hash = hash_ip(ip, ua)
    conn = get_conn()
    try:
        now = _utcnow_iso()
        try:
            conn.execute(
                "INSERT OR IGNORE INTO shares_hits(share_id, ip_hash, ua, created_at) VALUES(?,?,?,?)",
                (share_id, ip_hash, ua or None, now),
            )
            conn.commit()
        except Exception:
            pass
    finally:
        conn.close()


def get_share_progress(share_id: str) -> dict:
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT COUNT(DISTINCT ip_hash) FROM shares_hits WHERE share_id=? AND date(created_at)=date('now')",
            (share_id,),
        ).fetchone()
        uniq = int(row[0] or 0)
        goal = GOAL_DEFAULT
        return {"unique_visitors": uniq, "goal": goal, "unlocked": uniq >= goal}
    finally:
        conn.close()


def unlock_for_share(user_id: str, share_id: str) -> dict:
    conn = get_conn()
    try:
        prog = get_share_progress(share_id)
        if not prog.get('unlocked'):
            return {"granted": False}
        # Check already unlocked today
        import datetime
        day = datetime.datetime.utcnow().date().isoformat()
        row = conn.execute(
            "SELECT 1 FROM share_unlocks WHERE user_id=? AND day=?",
            (user_id, day),
        ).fetchone()
        if row:
            return {"granted": False}
        # Grant +1 renders today
        # Upsert usage_daily
        cur = conn.execute(
            "SELECT renders FROM usage_daily WHERE user_id=? AND day=?",
            (user_id, day),
        ).fetchone()
        if cur:
            conn.execute(
                "UPDATE usage_daily SET renders=renders+1 WHERE user_id=? AND day=?",
                (user_id, day),
            )
        else:
            conn.execute(
                "INSERT INTO usage_daily(user_id, day, renders, tts_sec) VALUES(?,?,?,0)",
                (user_id, day, 1),
            )
        # Record unlock
        conn.execute(
            "INSERT OR IGNORE INTO share_unlocks(user_id, day, share_id) VALUES(?,?,?)",
            (user_id, day, share_id),
        )
        conn.commit()
        return {"granted": True, "bonus": "renders", "amount": 1}
    finally:
        conn.close()
