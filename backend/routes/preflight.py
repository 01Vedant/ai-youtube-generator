from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter

router = APIRouter(tags=["preflight"])


@router.post("/api/preflight")
def preflight() -> Dict[str, Any]:
    errors: List[str] = []
    warnings: List[str] = []
    checks: List[Dict[str, str]] = []

    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path:
        checks.append({"name": "ffmpeg", "status": "pass"})
    else:
        checks.append({"name": "ffmpeg", "status": "warn"})
        warnings.append("ffmpeg not found in PATH (real renders may fail)")

    out_dir = Path("pipeline_outputs")
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
        probe = out_dir / ".write_test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        checks.append({"name": "output_dir_writable", "status": "pass"})
    except Exception as e:
        checks.append({"name": "output_dir_writable", "status": "fail"})
        errors.append(f"pipeline_outputs not writable: {e}")

    ok = len(errors) == 0
    return {"ok": ok, "errors": errors, "warnings": warnings, "checks": checks}
