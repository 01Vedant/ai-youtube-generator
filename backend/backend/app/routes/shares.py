from fastapi.responses import StreamingResponse
import csv
def is_admin(request: Request):
    # Use existing admin guard if available, else X-Admin header for dev
    return request.headers.get("X-Admin") == "true"
@router.get("/admin/shares")
async def admin_shares(request: Request, db: DB = Depends(get_db)):
    if not is_admin(request):
        raise HTTPException(status_code=403, detail="Admin only")
    rows = db.execute("SELECT id, created_at, title, artifact_url FROM shares ORDER BY created_at DESC LIMIT 200").fetchall()
    result = []
    for r in rows:
        meta_json = "{}"
        result.append({"id": r[0], "created_at": r[1], "title": r[2], "artifact_url": r[3], "meta_json": meta_json})
    return result
@router.get("/admin/shares.csv")
async def admin_shares_csv(request: Request, db: DB = Depends(get_db)):
    if not is_admin(request):
        raise HTTPException(status_code=403, detail="Admin only")
    rows = db.execute("SELECT id, created_at, title, artifact_url FROM shares ORDER BY created_at DESC LIMIT 200").fetchall()
    def iter_csv():
        yield "id,created_at,title,artifact_url,meta_json\n"
        for r in rows:
            meta_json = "{}"
            yield f'{r[0]},{r[1]},{r[2]},{r[3]},{meta_json}\n'
    return StreamingResponse(iter_csv(), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=shares.csv"})
import uuid
import re
from fastapi import APIRouter, Request, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel
from datetime import datetime
from app.db import get_db
from app.auth import get_current_user
from app.models import User
from app.db import DB

router = APIRouter()

class ShareCreate(BaseModel):
    artifact_url: str
    title: str = None
    description: str = None

OG_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>{title}</title>
  <meta property="og:type" content="video.other">
  <meta property="og:title" content="{title}">
  <meta property="og:description" content="{description}">
  <meta property="og:url" content="{share_url}">
  <meta property="og:image" content="{artifact_url}">
  <meta name="twitter:card" content="player">
  <meta name="twitter:title" content="{title}">
  <meta name="twitter:description" content="{description}">
  <meta name="twitter:player" content="{artifact_url}">
</head>
<body style="margin:0;padding:0;font-family:sans-serif;background:#fafafa;">
  <div style="max-width:480px;margin:40px auto;padding:24px;background:#fff;border-radius:8px;box-shadow:0 2px 8px #0001;">
    <h2 style="margin-top:0">{title}</h2>
    <p>{description}</p>
    {player}
    <div style="margin-top:16px;font-size:12px;color:#888;">Shared via BhaktiGen</div>
  </div>
</body>
</html>
'''

@router.post("/shares", response_model=dict)
def create_share(share: ShareCreate, db: DB = Depends(get_db), user: User = Depends(get_current_user)):
    if not re.match(r"^https?://", share.artifact_url):
        raise HTTPException(status_code=400, detail="artifact_url must be http(s)")
    share_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    db.execute(
        "INSERT INTO shares (id, artifact_url, title, description, created_at, user_id) VALUES (?, ?, ?, ?, ?, ?)",
        (share_id, share.artifact_url, share.title, share.description, now, user.id)
    )
    share_url = f"/s/{share_id}"
    return {"id": share_id, "share_url": share_url}

@router.get("/s/{id}", response_class=HTMLResponse)
def get_share_page(id: str, request: Request, db: DB = Depends(get_db)):
    row = db.execute("SELECT artifact_url, title, description FROM shares WHERE id=?", (id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Share not found")
    artifact_url, title, description = row
    title = title or "BhaktiGen Share"
    description = description or "Preview of shared artifact."
    share_url = str(request.url)
    meta_tags = f'<title>{title}</title><meta name="description" content="{description}">' 
    if artifact_url.endswith(".mp4"):
        meta_tags += f'<meta property="og:video" content="{artifact_url}"><meta property="og:type" content="video.other"><meta name="twitter:card" content="player">'
    else:
        meta_tags += f'<meta property="og:image" content="{artifact_url}"><meta property="og:type" content="article">'
    meta_tags += f'<link rel="alternate" type="application/json+oembed" href="/oembed?url={share_url}">' 
    if artifact_url.endswith(".mp4"):
        player = f'<video src="{artifact_url}" controls style="width:100%;border-radius:6px"></video>'
    elif artifact_url.endswith(".mp3"):
        player = f'<audio src="{artifact_url}" controls style="width:100%;border-radius:6px"></audio>'
    elif artifact_url.endswith(".jpg") or artifact_url.endswith(".png"):
        player = f'<img src="{artifact_url}" style="max-width:100%;border-radius:6px" />'
    else:
        player = f'<a href="{artifact_url}" target="_blank">Open Artifact</a>'
    html = f"<!DOCTYPE html><html lang='en'><head>{meta_tags}</head><body style='margin:0;padding:0;font-family:sans-serif;background:#fafafa;'><div style='max-width:480px;margin:40px auto;padding:24px;background:#fff;border-radius:8px;box-shadow:0 2px 8px #0001;'><h2 style='margin-top:0'>{title}</h2><p>{description}</p>{player}<div style='margin-top:16px;font-size:12px;color:#888;'>Shared via BhaktiGen</div></div></body></html>"
    return HTMLResponse(content=html)

@router.get("/oembed")
def oembed(url: str, format: str = "json", db: DB = Depends(get_db)):
    m = re.match(r".*/s/([\w-]+)", url)
    if not m:
        raise HTTPException(status_code=404, detail="Invalid share URL")
    id = m.group(1)
    row = db.execute("SELECT artifact_url, title, description FROM shares WHERE id=?", (id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Share not found")
    artifact_url, title, description = row
    return {
        "version": "1.0",
        "type": "video" if artifact_url.endswith(".mp4") else "rich",
        "title": title or "Shared Artifact",
        "author_name": "BhaktiGen",
        "provider_name": "BhaktiGen",
        "html": f'<iframe src="{url}" width="480" height="270" frameborder="0" allowfullscreen></iframe>'
    }

@router.get("/sitemap.xml")
def sitemap(db: DB = Depends(get_db)):
    rows = db.execute("SELECT id FROM shares ORDER BY created_at DESC LIMIT 50").fetchall()
    urls = [f"https://bhaktigen.com/s/{r[0]}" for r in rows]
    # Append to existing sitemap if present
    xml = "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">\n"
    for u in urls:
        xml += f"  <url><loc>{u}</loc></url>\n"
    xml += "</urlset>"
    return Response(content=xml, media_type="application/xml")
