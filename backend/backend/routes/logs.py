from datetime import datetime, timezone
from pathlib import Path
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
import io
import zipfile

from app.auth.guards import require_admin
from app.logs.structured import get_data_root


router = APIRouter()


def _parse_date(s: str | None) -> datetime:
    if not s:
        return datetime.now(timezone.utc).date().fromordinal(datetime.now(timezone.utc).date().toordinal())
    try:
        d = datetime.strptime(s, "%Y-%m-%d").date()
        return d
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid date format; use YYYY-MM-DD")


@router.get("/bundle")
def bundle_logs(include: str = "activity,structured", from_: str | None = None, to: str | None = None, user=Depends(require_admin)):
    data_root = get_data_root()
    logs_dir = data_root / "logs"
    activity_file = data_root / "activity.log"

    d_from = _parse_date(from_)
    d_to = _parse_date(to)
    if d_to < d_from:
        raise HTTPException(status_code=400, detail="Invalid range")

    includes = set([p.strip().lower() for p in include.split(',') if p.strip()])
    if not includes:
        includes = {"activity", "structured"}

    files: List[Path] = []
    # structured files per day
    if "structured" in includes:
        cur = d_from
        while cur <= d_to:
            fname = f"app-{cur.strftime('%Y-%m-%d')}.jsonl"
            p = logs_dir / fname
            if p.exists():
                files.append(p)
            cur = cur.fromordinal(cur.toordinal() + 1)
    # activity file
    if "activity" in includes and activity_file.exists():
        files.append(activity_file)

    if not files:
        # No files found
        return StreamingResponse(iter([b""]), status_code=204)

    mem = io.BytesIO()
    with zipfile.ZipFile(mem, mode="w", compression=zipfile.ZIP_DEFLATED) as z:
        for p in files:
            # ensure within data_root
            try:
                p.resolve().relative_to(data_root.resolve())
            except Exception:
                continue
            z.write(p, arcname=p.relative_to(data_root).as_posix())
    mem.seek(0)
    name = f"logs-{d_from.strftime('%Y-%m-%d')}_to_{d_to.strftime('%Y-%m-%d')}.zip"
    headers = {"Content-Disposition": f"attachment; filename={name}"}
    return StreamingResponse(mem, media_type="application/zip", headers=headers)
