async def test_add_review_requires_auth(client, make_movie):
    movie = await make_movie()
    r = await client.post(f"/v1/reviews/movies/{movie.id}", json={"rating": 8})
    assert r.status_code == 401


async def test_add_and_aggregate_review(client, make_movie, user_headers):
    movie = await make_movie()
    r = await client.post(
        f"/v1/reviews/movies/{movie.id}",
        json={"rating": 9, "comment": "Great"},
        headers=user_headers,
    )
    assert r.status_code == 201

    data = (await client.get(f"/v1/reviews/movies/{movie.id}")).json()
    assert data["count"] == 1
    assert data["average"] == 9.0
    assert data["reviews"][0]["comment"] == "Great"
    assert data["reviews"][0]["username"] == "regular"


async def test_duplicate_review_rejected(client, make_movie, user_headers):
    movie = await make_movie()
    await client.post(
        f"/v1/reviews/movies/{movie.id}", json={"rating": 9}, headers=user_headers
    )
    r = await client.post(
        f"/v1/reviews/movies/{movie.id}", json={"rating": 7}, headers=user_headers
    )
    assert r.status_code == 400


async def test_review_rating_out_of_bounds_422(client, make_movie, user_headers):
    movie = await make_movie()
    r = await client.post(
        f"/v1/reviews/movies/{movie.id}", json={"rating": 11}, headers=user_headers
    )
    assert r.status_code == 422


async def test_reviews_empty_aggregate(client, make_movie):
    movie = await make_movie()
    data = (await client.get(f"/v1/reviews/movies/{movie.id}")).json()
    assert data["count"] == 0
    assert data["average"] == 0
    assert data["reviews"] == []


async def test_reviews_list_endpoint(client, make_movie, user_headers):
    movie = await make_movie()
    # one user can only leave one review, so just verify the list endpoint shape
    await client.post(
        f"/v1/reviews/movies/{movie.id}", json={"rating": 8}, headers=user_headers
    )
    page = await client.get(f"/v1/reviews/movies/{movie.id}/list?offset=0&limit=6")
    assert page.status_code == 200
    assert len(page.json()) == 1
