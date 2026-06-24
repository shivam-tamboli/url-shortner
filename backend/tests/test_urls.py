import uuid


def unique_url() -> str:
    return f"https://test-{uuid.uuid4()}.example.com"


async def test_shorten_url_returns_short_code(client):
    response = await client.post("/api/shorten", json={"url": unique_url()})
    assert response.status_code == 200
    data = response.json()
    assert "short_code" in data
    assert "short_url" in data
    assert data["expires_at"] is None


async def test_same_url_returns_same_code(client):
    url = unique_url()
    r1 = await client.post("/api/shorten", json={"url": url})
    r2 = await client.post("/api/shorten", json={"url": url})
    assert r1.json()["short_code"] == r2.json()["short_code"]


async def test_redirect_returns_307(client):
    r1 = await client.post("/api/shorten", json={"url": unique_url()})
    code = r1.json()["short_code"]
    r2 = await client.get(f"/{code}", follow_redirects=False)
    assert r2.status_code == 307


async def test_unknown_code_returns_404(client):
    response = await client.get("/nonexistent-xyz-99999", follow_redirects=False)
    assert response.status_code == 404


async def test_custom_code_is_used(client):
    code = f"t-{uuid.uuid4().hex[:6]}"
    response = await client.post("/api/shorten", json={"url": unique_url(), "custom_code": code})
    assert response.status_code == 200
    assert response.json()["short_code"] == code


async def test_duplicate_custom_code_returns_409(client):
    code = f"d-{uuid.uuid4().hex[:6]}"
    await client.post("/api/shorten", json={"url": unique_url(), "custom_code": code})
    r2 = await client.post("/api/shorten", json={"url": unique_url(), "custom_code": code})
    assert r2.status_code == 409


async def test_stats_returns_click_count(client):
    r1 = await client.post("/api/shorten", json={"url": unique_url()})
    code = r1.json()["short_code"]
    r2 = await client.get(f"/api/stats/{code}")
    assert r2.status_code == 200
    assert r2.json()["clicks"] == 0


async def test_link_with_expiry_returns_expires_at(client):
    response = await client.post("/api/shorten", json={"url": unique_url(), "expiry_hours": 24})
    assert response.status_code == 200
    assert response.json()["expires_at"] is not None


async def test_invalid_custom_code_too_long_returns_422(client):
    response = await client.post("/api/shorten", json={
        "url": unique_url(),
        "custom_code": "waytoolongcode",
    })
    assert response.status_code == 422


async def test_invalid_custom_code_special_chars_returns_422(client):
    response = await client.post("/api/shorten", json={
        "url": unique_url(),
        "custom_code": "bad/code",
    })
    assert response.status_code == 422


async def test_expiry_hours_zero_returns_422(client):
    response = await client.post("/api/shorten", json={
        "url": unique_url(),
        "expiry_hours": 0,
    })
    assert response.status_code == 422


async def test_health_check(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
