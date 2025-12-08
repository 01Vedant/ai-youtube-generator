from fastapi import APIRouter, Response, Depends, HTTPException, Request
from typing import Any, Dict, List, Optional
import re
import json
from datetime import datetime, timezone

from app.db import get_conn, waitlist_add, waitlist_list

router = APIRouter()

# Placeholder auth dependency; replace with project-specific user retrieval
def get_current_user() -> Dict[str, Any]:
  return {"id": "dev-user", "roles": []}

def require_admin(user: Dict[str, Any]) -> None:
  if "admin" not in (user.get("roles") or []):
    raise HTTPException(status_code=403, detail="Forbidden")

@router.get("/robots.txt")
def robots_txt() -> Response:
  body = "User-agent: *\nAllow: /\nSitemap: /public/sitemap.xml\n"
  return Response(content=body, media_type="text/plain")

@router.get("/sitemap.xml")
def sitemap_xml() -> Response:
  # URLs
  urls: List[Dict[str, str]] = [
    {"loc": "/", "lastmod": datetime.now(timezone.utc).isoformat()},
    {"loc": "/templates/public", "lastmod": datetime.now(timezone.utc).isoformat()},
  ]
  # Add latest 50 builtin/shared templates
  try:
    conn = get_conn()
    cur = conn.execute(
      """
      SELECT id, created_at FROM templates
      WHERE visibility IN ('public','builtin','shared')
      ORDER BY created_at DESC
      LIMIT 50
      """
    )
    rows = cur.fetchall()
    for r in rows:
      urls.append({"loc": f"/templates/{r[0]}", "lastmod": (r[1] or datetime.now(timezone.utc).isoformat())})
  except Exception:
    pass
  finally:
    try: conn.close()
    except Exception: pass

  # Build XML
  import os
  base = os.getenv('APP_BASE_URL')
  def _abs(loc: str) -> str:
    return (base.rstrip('/') + loc) if base else loc
  items = [f"  <url><loc>{_abs(u['loc'])}</loc><lastmod>{u['lastmod']}</lastmod></url>" for u in urls]
  xml = "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">\n" + "\n".join(items) + "\n</urlset>\n"
  return Response(content=xml, media_type="application/xml")

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# In-memory rate limit per IP: 1 req/15s and 10/day
_RL_WINDOW: Dict[str, Dict[str, Any]] = {}

def _rate_limit_guard(ip: str) -> Optional[Dict[str, Any]]:
  import time
  now = time.time()
  rec = _RL_WINDOW.get(ip)
  if not rec:
    _RL_WINDOW[ip] = { 'last_ts': now, 'day': datetime.now(timezone.utc).date().isoformat(), 'count': 1 }
    return None
  # reset daily window
  day = datetime.now(timezone.utc).date().isoformat()
  if rec.get('day') != day:
    rec['day'] = day; rec['count'] = 0
  # 1 per 15s
  last_ts = rec.get('last_ts', 0)
  if now - last_ts < 15:
    reset = datetime.fromtimestamp(last_ts + 15, tz=timezone.utc).isoformat()
    return { 'code':'QUOTA_EXCEEDED', 'detail': { 'metric':'waitlist/ip', 'limit':'1/15s', 'reset_at': reset } }
  rec['last_ts'] = now
  rec['count'] = int(rec.get('count', 0)) + 1
  if rec['count'] > 10:
    # next day reset time (start of next day UTC)
    next_day = datetime.combine(datetime.now(timezone.utc).date(), datetime.min.time(), tzinfo=timezone.utc).isoformat()
    return { 'code':'QUOTA_EXCEEDED', 'detail': { 'metric':'waitlist/ip', 'limit':'10/day', 'reset_at': next_day } }
  return None

@router.post("/waitlist")
def post_waitlist(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
  ip = request.client.host if request and request.client else 'unknown'
  rl = _rate_limit_guard(ip)
  if rl:
    raise HTTPException(status_code=429, detail=rl)
  email = (payload.get("email") or "").strip().lower()
  source = (payload.get("source") or None)
  meta = payload.get("meta")
  if not EMAIL_RE.match(email):
    raise HTTPException(status_code=400, detail="Invalid email")
  added = waitlist_add(email, source, meta if isinstance(meta, dict) else None)
  return {"ok": True, **({"duplicate": True} if not added else {})}

@router.get("/og/template/{id}")
def og_template(id: str) -> Dict[str, Any]:
  try:
    conn = get_conn()
    cur = conn.execute("SELECT title, description, thumb FROM templates WHERE id = ?", (id,))
    row = cur.fetchone()
    if not row:
      raise HTTPException(status_code=404, detail="Not found")
    return {"title": row[0], "description": row[1] or "", "image": row[2] or ""}
  finally:
    try: conn.close()
    except Exception: pass

@router.get("/admin/waitlist.csv")
def admin_waitlist_csv(user: Dict[str, Any] = Depends(get_current_user)) -> Response:
  require_admin(user)
  rows = waitlist_list(1000)
  lines = ["email,created_at,source"] + [f"{r['email']},{r['created_at']},{r['source'] or ''}" for r in rows]
  csv = "\n".join(lines) + "\n"
  headers = {
    "Content-Type": "text/csv",
    "Content-Disposition": "attachment; filename=waitlist.csv",
  }
  return Response(content=csv, media_type="text/csv", headers=headers)