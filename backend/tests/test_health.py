def test_live_ok():
def test_ready_db_failure(monkeypatch):
def test_version(client):
    resp = client.get("/version")
    assert resp.status_code == 200
    assert "version" in resp.json()

def test_status(client):
    resp = client.get("/status")
    assert resp.status_code == 200
    r = health.ready()
    assert r.get('ok') is True


def test_version_and_metrics():
    v = health.version()
    assert 'version' in v and 'git_sha' in v and 'started_at' in v

    res = health.metrics()
    body = res.body.decode('utf-8') if hasattr(res, 'body') else str(res)
    # Required metric names present
    assert 'renders_started_total' in body
    assert 'renders_completed_total' in body
    assert 'renders_failed_total' in body
    assert 'tts_seconds_total' in body
