from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse

router = APIRouter(prefix="/legal", tags=["legal"])

LEGAL_DIR = Path(__file__).resolve().parent.parent / "docs" / "legal"
ALLOWED = {"terms", "privacy", "cookies", "imprint"}


def md_to_simple_html(md: str) -> str:
    lines = md.splitlines()
    html_parts = ["<article>"]
    for line in lines:
        if line.startswith("# "):
            html_parts.append(f"<h1>{line[2:].strip()}</h1>")
        elif line.startswith("## "):
            html_parts.append(f"<h2>{line[3:].strip()}</h2>")
        elif line.strip() == "":
            continue
        else:
            html_parts.append(f"<p>{line.strip()}</p>")
    html_parts.append("</article>")
    return "".join(html_parts)


@router.get("/{slug}", response_class=HTMLResponse)
def legal_page(slug: str):
    if slug not in ALLOWED:
        raise HTTPException(status_code=404, detail="Not Found")
    fp = LEGAL_DIR / f"{slug}.md"
    if not fp.exists():
        raise HTTPException(status_code=404, detail="Not Found")
    content = fp.read_text(encoding="utf-8")
    html = md_to_simple_html(content)
    return HTMLResponse(content=html, media_type="text/html; charset=utf-8")