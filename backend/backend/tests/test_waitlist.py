def test_waitlist_post_and_duplicate(client):
    r = client.post("/public/waitlist", json={"email": "test@example.com"})
    assert r.status_code == 200
    assert r.json().get("ok")
    r2 = client.post("/public/waitlist", json={"email": "test@example.com"})
    assert r2.status_code == 200
    assert r2.json().get("duplicate")
    site = sitemap_xml()
    assert site.media_type == 'application/xml'