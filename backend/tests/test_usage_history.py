from __future__ import annotations
import datetime

from fastapi.testclient import TestClient

from backend.backend.main import app
from app.db import get_conn

client = TestClient(app)


def seed_usage(user_id: str, day: str, renders: int, tts_sec: int):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT OR REPLACE INTO usage_daily (user_id, day, renders, tts_sec) VALUES (?, ?, ?, ?)",
        (user_id, day, renders, tts_sec),
    )
    conn.commit()


def test_usage_history_gap_fill_and_privacy():
    # Setup two users
    user_a = "user-a"
    user_b = "user-b"

    # Compute recent days
    today = datetime.date.today().isoformat()
    d1 = (datetime.date.today() - datetime.timedelta(days=4)).isoformat()
    d2 = (datetime.date.today() - datetime.timedelta(days=3)).isoformat()
    d3 = (datetime.date.today() - datetime.timedelta(days=2)).isoformat()
    d4 = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()

    # Seed A across 5 days mixed
    seed_usage(user_a, d1, 1, 30)
    seed_usage(user_a, d2, 0, 15)
    seed_usage(user_a, d3, 3, 0)
    seed_usage(user_a, d4, 2, 20)
    seed_usage(user_a, today, 1, 10)

    # Authenticate as user A (assuming test helper issues token or mock)
    # Here we rely on get_current_user reading from a header X-User-Id for tests if supported.
    # If not available, this test should be adapted to the project's auth test utilities.

    headers_a = {"X-User-Id": user_a}
    resp = client.get("/usage/history?days=14", headers=headers_a)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["days"] == 14
    series = data["series"]
    # Ensure ordering ascending by day and window length matches
    assert len(series) == 14
    days_list = [p["day"] for p in series]
    assert days_list[0] <= days_list[-1]
    # Check zeros filled for non-seeded gaps
    assert all(isinstance(p["renders"], int) for p in series)
    assert all(isinstance(p["tts_sec"], int) for p in series)
    # Totals for seeded days
    total_renders = sum(p["renders"] for p in series)
    total_tts = sum(p["tts_sec"] for p in series)
    assert total_renders >= (1 + 0 + 3 + 2 + 1)
    assert total_tts >= (30 + 15 + 0 + 20 + 10)

    # User B sees zeros across window
    headers_b = {"X-User-Id": user_b}
    resp_b = client.get("/usage/history?days=14", headers=headers_b)
    assert resp_b.status_code == 200
    data_b = resp_b.json()
    series_b = data_b["series"]
    assert len(series_b) == 14
    assert sum(p["renders"] for p in series_b) == 0
    assert sum(p["tts_sec"] for p in series_b) == 0
