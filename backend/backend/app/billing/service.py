from __future__ import annotations
from typing import Optional
from datetime import datetime

from app.db import get_conn


def get_or_create_customer(user_id: str, email: str, stripe_customer_id: Optional[str]) -> str:
    conn = get_conn()
    try:
        if stripe_customer_id:
            # Persist if missing
            conn.execute(
                "INSERT OR IGNORE INTO billing (user_id, stripe_customer_id, status) VALUES (?,?,?)",
                (user_id, stripe_customer_id, "free"),
            )
            conn.commit()
            return stripe_customer_id
        # Try existing
        row = conn.execute(
            "SELECT stripe_customer_id FROM billing WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        if row and row[0]:
            return row[0]
        raise RuntimeError("stripe_customer_id required to create")
    finally:
        conn.close()


def ensure_customer(user_id: str, customer_id: str) -> None:
    conn = get_conn()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO billing (user_id, stripe_customer_id, status) VALUES (?,?, COALESCE((SELECT status FROM billing WHERE user_id = ?), 'free'))",
            (user_id, customer_id, user_id),
        )
        conn.commit()
    finally:
        conn.close()


def set_subscription(user_id: str, sub_id: str, status: str, current_period_end_iso: Optional[str]) -> None:
    conn = get_conn()
    try:
        conn.execute(
            "UPDATE billing SET stripe_sub_id = ?, status = ?, current_period_end = ? WHERE user_id = ?",
            (sub_id, status, current_period_end_iso, user_id),
        )
        # Update plan on users table
        plan_id = "pro" if status in ("active", "trialing") else "free"
        conn.execute("UPDATE users SET plan_id = ? WHERE id = ?", (plan_id, user_id))
        conn.commit()
    finally:
        conn.close()


def clear_subscription(user_id: str) -> None:
    conn = get_conn()
    try:
        conn.execute(
            "UPDATE billing SET stripe_sub_id = NULL, status = 'canceled', current_period_end = NULL WHERE user_id = ?",
            (user_id,),
        )
        conn.execute("UPDATE users SET plan_id = 'free' WHERE id = ?", (user_id,))
        conn.commit()
    finally:
        conn.close()
