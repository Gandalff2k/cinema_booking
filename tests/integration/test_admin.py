NEW_MOVIE = {"title": "New Movie", "duration_minutes": 100, "age_rating": "16+"}


async def test_admin_requires_token(client):
    assert (await client.get("/v1/admin/stats")).status_code == 401


async def test_admin_forbidden_for_normal_user(client, user_headers):
    assert (
        await client.get("/v1/admin/stats", headers=user_headers)
    ).status_code == 403


async def test_admin_stats(client, admin_headers, make_movie):
    await make_movie()
    r = await client.get("/v1/admin/stats", headers=admin_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["movies"] >= 1
    assert "revenue" in body and "avg_rating" in body


async def test_admin_create_movie(client, admin_headers):
    r = await client.post("/v1/admin/movies", json=NEW_MOVIE, headers=admin_headers)
    assert r.status_code == 201
    assert r.json()["title"] == "New Movie"


async def test_admin_movies_pagination(client, admin_headers):
    for i in range(15):
        await client.post(
            "/v1/admin/movies",
            json={"title": f"Movie {i}", "duration_minutes": 90},
            headers=admin_headers,
        )
    page1 = await client.get(
        "/v1/admin/movies?offset=0&limit=10", headers=admin_headers
    )
    page2 = await client.get(
        "/v1/admin/movies?offset=10&limit=10", headers=admin_headers
    )
    assert len(page1.json()) == 10
    assert len(page2.json()) == 5


async def test_admin_movie_search(client, admin_headers):
    await client.post(
        "/v1/admin/movies",
        json={"title": "Batman Begins", "duration_minutes": 90},
        headers=admin_headers,
    )
    await client.post(
        "/v1/admin/movies",
        json={"title": "Superman", "duration_minutes": 90},
        headers=admin_headers,
    )
    r = await client.get("/v1/admin/movies?search=batman", headers=admin_headers)
    assert [m["title"] for m in r.json()] == ["Batman Begins"]


async def test_admin_soft_delete_movie(client, admin_headers, make_movie):
    movie = await make_movie(title="ToHide")
    r = await client.delete(f"/v1/admin/movies/{movie.id}", headers=admin_headers)
    assert r.status_code == 200
    # now hidden from the public listing
    listing = (await client.get("/v1/movies")).json()
    assert all(m["title"] != "ToHide" for m in listing)


async def test_admin_orders_email_filter_empty(client, admin_headers):
    r = await client.get("/v1/admin/orders?email=nobody@x.com", headers=admin_headers)
    assert r.status_code == 200
    assert r.json() == []
