import os, sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
APP = ROOT / 'app'
for p in (ROOT, APP):
    sp = str(p)
    if sp not in sys.path:
        sys.path.insert(0, sp)

from app.routes.legal import legal_page

def test_privacy_returns_html_contains_h1():
    resp = legal_page('privacy')
    html = resp.body.decode('utf-8')
    assert ('<h1>' in html) or ('Privacy' in html)

def test_invalid_slug_404():
    from fastapi import HTTPException
    try:
        legal_page('unknown')
        assert False, 'Expected 404'
    except HTTPException as e:
        assert e.status_code == 404
