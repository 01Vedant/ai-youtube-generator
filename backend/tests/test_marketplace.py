def auth_headers():
def seed_templates():
def test_marketplace_templates(client):
    r = client.get("/marketplace/templates")
    assert r.status_code == 200
    items = r.json()
    if items:
        tid = items[0]["id"]
        r2 = client.get(f"/marketplace/templates/{tid}")
        assert r2.status_code == 200
        conn.close()


def test_marketplace_listing_and_duplicate():
    init_db()
    seed_templates()

    # List marketplace (should include builtin and shared only)
    data = list_marketplace_templates()
    ids = [it["id"] for it in data["items"]]
    assert "tpl_builtin_a" in ids and "tpl_shared_b" in ids
    assert "tpl_private_c" not in ids

    # Search
    data = list_marketplace_templates(q="Official")
    assert any(it["id"] == "tpl_builtin_a" for it in data["items"])  # match title

    # Get single template
    tpl = get_marketplace_template("tpl_shared_b")
    assert tpl["visibility"] == "shared"

    # Duplicate shared (pretend authenticated user via test headers stub)
    new_tpl = duplicate_marketplace_template("tpl_shared_b", user=_DummyUser({"id": "uTest"}))
    assert new_tpl["visibility"] == "private"
    assert new_tpl["title"].startswith("Copy of ")
    # downloads increments
    conn = get_conn()
    try:
        row = conn.execute("SELECT downloads FROM templates WHERE id='tpl_shared_b'").fetchone()
        assert int(row[0]) >= 4
    finally:
        conn.close()

    # Private template from other owner should be forbidden
    from fastapi import HTTPException
    try:
        duplicate_marketplace_template("tpl_private_c", user=_DummyUser({"id": "another"}))
        assert False, "Expected forbidden"
    except HTTPException as e:
        assert e.status_code in (401, 403)
