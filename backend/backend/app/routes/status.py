from __future__ import annotations
from fastapi import APIRouter
from app.db import get_conn

router = APIRouter()

@router.get('/status.json')
def status_json():
    conn = get_conn()
    try:
        row = conn.execute("SELECT COUNT(1) AS c FROM job_queue").fetchone()
        return {"jobs_total": int(row[0]) if row else 0, "ok": True}
    finally:
        conn.close()

@router.get('/status')
def status_page():
    return {"html": "<html><body><h1>Status OK</h1></body></html>"}
