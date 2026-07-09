from core.config import config



async def test_login_is_rate_limited_per_ip(client, monkeypatch):

    monkeypatch.setattr(config, "RATE_LIMIT_ENABLED", True)

    payload = {"contact": "nobody@example.com", "password": "wrong"}
    statuses = [
        (await client.post("/v1/auth/login", json=payload)).status_code
        for _ in range(4)
    ]

    assert statuses[:3] == [400, 400, 400]
    assert statuses[3] == 429


async def test_rate_limit_is_per_route(client, monkeypatch):

    monkeypatch.setattr(config, "RATE_LIMIT_ENABLED", True)

    login_payload = {"contact": "nobody@example.com", "password": "wrong"}
    for _ in range(3):
        await client.post("/v1/auth/login", json=login_payload)
    limited = await client.post("/v1/auth/login", json=login_payload)
    assert limited.status_code == 429

    register_payload = {
        "email": "fresh@example.com",
        "username": "freshuser",
        "password": "password123",
    }
    still_allowed = await client.post("/v1/auth/register", json=register_payload)
    assert still_allowed.status_code == 201
