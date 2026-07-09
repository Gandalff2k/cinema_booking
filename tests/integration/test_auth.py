CREDS = {"email": "alice@example.com", "username": "alice", "password": "password123"}


async def test_register_returns_user(client):
    r = await client.post("/v1/auth/register", json=CREDS)
    assert r.status_code == 201
    body = r.json()
    assert body["email"] == CREDS["email"]
    assert body["role"] == "client"


async def test_register_duplicate_email(client):
    await client.post("/v1/auth/register", json=CREDS)
    r = await client.post("/v1/auth/register", json={**CREDS, "username": "alice2"})
    assert r.status_code == 400


async def test_register_short_password_422(client):
    r = await client.post("/v1/auth/register", json={**CREDS, "password": "short"})
    assert r.status_code == 422


async def test_login_and_me(client):
    await client.post("/v1/auth/register", json=CREDS)
    r = await client.post(
        "/v1/auth/login",
        json={"contact": CREDS["email"], "password": CREDS["password"]},
    )
    assert r.status_code == 200
    token = r.json()["access_token"]
    me = await client.get("/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["username"] == "alice"


async def test_login_wrong_password(client):
    await client.post("/v1/auth/register", json=CREDS)
    r = await client.post(
        "/v1/auth/login", json={"contact": CREDS["email"], "password": "nope"}
    )
    assert r.status_code == 400


async def test_me_requires_auth(client):
    assert (await client.get("/v1/auth/me")).status_code == 401


async def test_me_rejects_garbage_token(client):
    r = await client.get("/v1/auth/me", headers={"Authorization": "Bearer x.y.z"})
    assert r.status_code == 401


async def test_no_duplicate_unrated_limited_auth_routes(client):
    """Regression: register/login must only be reachable via the rate-limited
    /v1/auth/* routes. A duplicate /v1/users/register|login previously bypassed
    the rate limiter entirely. GET /v1/users/ still exists (admin listing), so
    POST there is 405 (method not allowed), not a live registration endpoint."""
    assert (await client.post("/v1/users/", json=CREDS)).status_code == 405
    assert (
        await client.post("/v1/users/login", json={"contact": "x", "password": "y"})
    ).status_code == 404


async def test_users_list_requires_admin(client, user_headers):
    r = await client.get("/v1/users/", headers=user_headers)
    assert r.status_code == 403


async def test_password_change_flow(client, user_headers):
    r = await client.put(
        "/v1/users/me/password",
        json={"old_password": "password123", "new_password": "newpassword1"},
        headers=user_headers,
    )
    assert r.status_code == 200
    ok = await client.post(
        "/v1/auth/login",
        json={"contact": "user@example.com", "password": "newpassword1"},
    )
    assert ok.status_code == 200
    old = await client.post(
        "/v1/auth/login",
        json={"contact": "user@example.com", "password": "password123"},
    )
    assert old.status_code == 400
