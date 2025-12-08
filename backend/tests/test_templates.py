def test_templates_endpoints(client):
    r = client.get("/templates/builtin")
    assert r.status_code == 200
    templates = r.json()
    assert isinstance(templates, list)
    if templates:
        tid = templates[0]["id"]
        r = client.post(f"/templates/{tid}/preview-plan", json={"input": "test"})
        assert r.status_code == 200
        r = client.post(f"/templates/{tid}/render", json={"input": "test"})
        assert r.status_code == 200
        assert "job_id" in r.json()
