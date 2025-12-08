from __future__ import annotations

from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import HTMLResponse, PlainTextResponse
from hashlib import sha256
from datetime import datetime

from app.db import get_conn
from app.auth.security import get_current_user
from app.auth.guards import forbid
from app.shares.models import ShareCreate, ShareInfo
from app.shares.util import new_share_id
from app.artifacts_storage.factory import get_storage
from app.plans.guards import require_feature as require_plan_feature
from app.auth.guards import require_feature as require_global_feature
from app.growth.service import record_share_hit

router = APIRouter()


def _utcnow_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _ensure_owner(job_id: str, user) -> None:
    if not user:
        forbid()
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT user_id FROM jobs_index WHERE id = ?",
            (job_id,),
        ).fetchone()
        if not row or row["user_id"] != user["id"]:
            forbid()
    finally:
        conn.close()


@router.post("/shares")
def create_share(req: ShareCreate, user=Depends(get_current_user)) -> dict:
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    # Feature gate (Free has it, but enforce for completeness)
    require_global_feature("public_shares")
    require_plan_feature(user.get("plan_id", "free"), "share_links")
    _ensure_owner(req.job_id, user)
    share_id = new_share_id(24)
    conn = get_conn()
    try:
        conn.execute(
            "INSERT INTO shares (share_id, job_id, user_id, created_at, revoked) VALUES (?,?,?,?,0)",
            (share_id, req.job_id, user["id"], _utcnow_iso()),
        )
        conn.commit()
    finally:
        conn.close()
    return {"share_id": share_id, "url": f"/s/{share_id}"}


@router.post("/shares/{share_id}/revoke")
def revoke_share(share_id: str, user=Depends(get_current_user)) -> dict:
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    conn = get_conn()
    try:
        row = conn.execute("SELECT job_id, user_id, revoked FROM shares WHERE share_id = ?", (share_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Not found")
        if row["user_id"] != user["id"]:
            forbid()
        if int(row["revoked"] or 0) == 1:
            return {"ok": True}
        conn.execute("UPDATE shares SET revoked = 1 WHERE share_id = ?", (share_id,))
        conn.commit()
        return {"ok": True}
    finally:
        conn.close()


CRAWLER_UA = (
    "googlebot",
    "facebookexternalhit",
    "twitterbot",
    "slackbot",
    "discordbot",
)

def _record_share_view(conn, share_id: str, request: Request) -> None:
    try:
        # ensure table
        conn.execute(
            "CREATE TABLE IF NOT EXISTS share_views (id TEXT PRIMARY KEY, share_id TEXT, ts TEXT, ip_hash TEXT, ua TEXT, referer TEXT)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_share_views_share_id_ts ON share_views(share_id, ts)"
        )
        ip = request.client.host if request.client else "0.0.0.0"
        salt = (request.app.state.config.get("SECRET_SALT") if getattr(request.app.state, "config", None) else "") or ""
        ip_hash = sha256((ip + salt).encode("utf-8")).hexdigest()[:16]
        ua = request.headers.get("user-agent") or ""
        referer = request.headers.get("referer") or ""
        vid = sha256((share_id + ip_hash + _utcnow_iso()).encode("utf-8")).hexdigest()[:24]
        conn.execute(
            "INSERT INTO share_views (id, share_id, ts, ip_hash, ua, referer) VALUES (?,?,?,?,?,?)",
            (vid, share_id, _utcnow_iso(), ip_hash, ua, referer),
        )
        conn.commit()
    except Exception:
        pass


@router.get("/s/{share_id}")
def get_shared_view(share_id: str, request: Request) -> HTMLResponse | dict:
    require_global_feature("public_shares")
    conn = get_conn()
    try:
        srow = conn.execute("SELECT job_id, user_id, created_at, revoked FROM shares WHERE share_id = ?", (share_id,)).fetchone()
        if not srow or int(srow["revoked"] or 0) == 1:
            raise HTTPException(status_code=404, detail="Not found")
        job_id = srow["job_id"]
        jrow = conn.execute("SELECT title, created_at FROM jobs_index WHERE id = ?", (job_id,)).fetchone()
        title = (jrow["title"] if jrow else job_id) or job_id
        created_at = (jrow["created_at"] if jrow else srow["created_at"]) or srow["created_at"]
        # record view best-effort
        _record_share_view(conn, share_id, request)
    finally:
        conn.close()

    storage = get_storage()
    payload = {
        "job_id": job_id,
        "title": title,
        "created_at": created_at,
        "artifacts": {
            "thumbnail": storage.get_url(f"{job_id}/thumb.png"),
            "video": storage.get_url(f"{job_id}/final.mp4"),
            "audio": storage.get_url(f"{job_id}/tts.wav"),
        },
    }

    ua = (request.headers.get("user-agent") or "").lower()
    html_mode = any(b in ua for b in CRAWLER_UA) or (request.query_params.get("html") == "1")
    if html_mode:
        base = request.url.scheme + "://" + request.url.hostname + (":" + str(request.url.port) if request.url.port else "")
        og_image = payload["artifacts"]["thumbnail"]
        og_video = payload["artifacts"]["video"]
        meta = f"""
<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\"/>
  <title>{title}</title>
  <link rel=\"canonical\" href=\"{base}/s/{share_id}\"/>
  <meta property=\"og:title\" content=\"{title}\"/>
  <meta property=\"og:description\" content=\"AI-generated video\"/>
  <meta property=\"og:type\" content=\"video.other\"/>
  <meta property=\"og:image\" content=\"{og_image}\"/>
  <meta property=\"og:video\" content=\"{og_video}\"/>
  <meta property=\"og:video:type\" content=\"video/mp4\"/>
  <meta property=\"og:video:width\" content=\"1080\"/>
  <meta property=\"og:video:height\" content=\"1920\"/>
  <meta name=\"twitter:card\" content=\"player\"/>
  <meta name=\"twitter:title\" content=\"{title}\"/>
  <meta name=\"twitter:image\" content=\"{og_image}\"/>
</head>
<body style=\"margin:0;padding:16px;font-family:system-ui,Segoe UI,Roboto\">\n
  <h1 style=\"font-size:16px;margin:0 0 8px\">{title}</h1>
  <video controls playsinline preload=\"metadata\" poster=\"{og_image}\" style=\"max-width:100%;height:auto;border:1px solid #eee\">\n
    <source src=\"{og_video}\" type=\"video/mp4\"/>
  </video>
  <p style=\"font-size:12px\"><a href=\"{base}/s/{share_id}\">View in app</a></p>
</body>
</html>
"""
        return HTMLResponse(content=meta)

    return payload

@router.post("/s/{share_id}/hit")
async def record_shared_hit(share_id: str, request: Request) -> dict:
    require_global_feature("public_shares")
    try:
        ip = request.client.host if request.client else '0.0.0.0'
        ua = request.headers.get('user-agent')
        record_share_hit(share_id, ip, ua)
        try:
            log_json("share_hit", share_id=share_id)
        except Exception:
            pass
    except Exception:
        pass
    return {"ok": True}


@router.get("/oembed")
def oembed(url: str, request: Request) -> dict:
    # Minimal oEmbed for share URLs
    try:
        base = request.url.scheme + "://" + request.url.hostname + (":" + str(request.url.port) if request.url.port else "")
        if not url.startswith(base + "/s/"):
            raise HTTPException(status_code=400, detail="unsupported")
        share_id = url.rsplit("/", 1)[-1]
        conn = get_conn()
        try:
            srow = conn.execute("SELECT job_id, revoked FROM shares WHERE share_id = ?", (share_id,)).fetchone()
            if not srow or int(srow["revoked"] or 0) == 1:
                raise HTTPException(status_code=404, detail="Not found")
            job_id = srow["job_id"]
        finally:
            conn.close()
        storage = get_storage()
        thumb = storage.get_url(f"{job_id}/thumb.png")
        width = 1080
        height = 1920
        iframe = f"<iframe src=\"{base}/s/{share_id}?html=1\" width=\"{width}\" height=\"{height}\" frameborder=\"0\" allowfullscreen></iframe>"
        return {"type": "video", "version": "1.0", "title": job_id, "thumbnail_url": thumb, "html": iframe, "width": width, "height": height}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=400, detail="bad_request")


@router.get("/robots.txt")
def robots_txt() -> PlainTextResponse:
    content = "User-agent: *\nAllow: /s/\nDisallow: /api/\n"
    return PlainTextResponse(content=content)


@router.get("/sitemap.xml")
def sitemap_xml() -> PlainTextResponse:
    conn = get_conn()
    try:
        rows = conn.execute("SELECT share_id, created_at FROM shares WHERE revoked = 0 ORDER BY created_at DESC LIMIT 500").fetchall()
    finally:
        conn.close()
    items = []
    items.append("<?xml version=\"1.0\" encoding=\"UTF-8\"?>")
    items.append("<urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">")
    for r in rows:
        items.append(f"  <url><loc>/s/{r['share_id']}</loc><lastmod>{r['created_at']}</lastmod></url>")
    items.append("</urlset>")
    return PlainTextResponse(content="\n".join(items), media_type="application/xml")
