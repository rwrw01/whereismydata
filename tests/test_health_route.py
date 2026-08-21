async def test_healthz_returns_ok(client):
    response = await client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_readyz_returns_ok(client):
    response = await client.get("/readyz")
    assert response.status_code == 200
