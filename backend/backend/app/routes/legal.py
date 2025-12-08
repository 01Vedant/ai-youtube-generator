from __future__ import annotations
from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from pathlib import Path
import re

router = APIRouter()

LEGAL_DIR = Path(__file__).resolve().parents[2] / "app" / "legal"
ALLOWED = {"terms", "privacy", "cookies", "imprint"}

def md_to_simple_html(md: str) -> str:
    # Very simple converter: supports h1-h3, p, a, ul/ol, li
    html = md
    html = re.sub(r"^# (.*)$", r"<h1>\\1</h1>", html, flags=re.MULTILINE)
    html = re.sub(r"^## (.*)$", r"<h2>\\1</h2>", html, flags=re.MULTILINE)
    html = re.sub(r"^### (.*)$", r"<h3>\\1</h3>", html, flags=re.MULTILINE)
    # Links [text](url)
    html = re.sub(r"\[(.*?)\]\((.*?)\)", r"<a href=\"\\2\">\\1</a>", html)
    # Lists
    html = re.sub(r"^\* (.*)$", r"<ul><li>\\1</li></ul>", html, flags=re.MULTILINE)
    html = re.sub(r"^\d+\. (.*)$", r"<ol><li>\\1</li></ol>", html, flags=re.MULTILINE)
    # Paragraphs: wrap bare lines
    lines = [l.strip() for l in html.splitlines()]
    out = []
    for l in lines:
        if l.startswith("<h") or l.startswith("<ul>") or l.startswith("<ol>") or l.startswith("<a "):
            out.append(l)
        elif l:
            out.append(f"<p>{l}</p>")
    return "\n".join(out)

@router.get("/{page}")
def legal_page(page: str):
    if page not in ALLOWED:
        raise HTTPException(status_code=404, detail="Not found")
    fp = LEGAL_DIR / f"{page}.md"
    if not fp.exists():
        raise HTTPException(status_code=404, detail="Not found")
    md = fp.read_text(encoding="utf-8")
    html = md_to_simple_html(md)
    resp = HTMLResponse(content=html)
    resp.headers["Cache-Control"] = "public, max-age=300"
    return resp
