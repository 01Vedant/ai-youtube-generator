from __future__ import annotations
from fastapi import APIRouter

router = APIRouter()

@router.post('/request-export')
def request_export():
    return {"ok": True, "job_id": "export-simulated"}

@router.post('/request-delete')
def request_delete():
    return {"ok": True, "job_id": "delete-simulated"}
