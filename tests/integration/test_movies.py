async def test_movies_empty(client):
    r = await client.get("/v1/movies")
    assert r.status_code == 200
    assert r.json() == []


async def test_movies_lists_created(client, make_movie):
    await make_movie(title="Dune")
    titles = [m["title"] for m in (await client.get("/v1/movies")).json()]
    assert "Dune" in titles


async def test_movie_by_id(client, make_movie):
    movie = await make_movie(title="Oppenheimer")
    r = await client.get(f"/v1/movies/{movie.id}")
    assert r.status_code == 200
    assert r.json()["title"] == "Oppenheimer"


async def test_movie_by_id_404(client):
    assert (await client.get("/v1/movies/99999")).status_code == 404


async def test_inactive_movie_is_hidden(client, make_movie):
    movie = await make_movie(title="Hidden", active=False)
    assert (await client.get(f"/v1/movies/{movie.id}")).status_code == 404
    listing = (await client.get("/v1/movies")).json()
    assert all(m["title"] != "Hidden" for m in listing)


async def test_popular_empty_without_cache(client):
    r = await client.get("/v1/movies/popular")
    assert r.status_code == 200
    assert r.json() == []


async def test_shows_endpoint_empty(client, make_movie):
    movie = await make_movie()
    r = await client.get(f"/v1/movies/shows/{movie.id}")
    assert r.status_code == 200
    assert r.json() == []
