import json

from fastapi import APIRouter, Depends

from app.repositories import CinemaRepository
from app.schemas.responses.cinema import MovieResponse, ShowResponse
from core.cache import Cache
from core.cache.redis_backend import redis
from core.exceptions import NotFoundException
from core.factory import Factory
from worker.tasks.cache_tasks import POPULAR_KEY

movies_router = APIRouter(prefix="/movies", tags=["Movies"])


@movies_router.get("", response_model=list[MovieResponse])
@Cache.cached(prefix="movies", ttl=900)
async def get_movies(
    cinema_repository: CinemaRepository = Depends(Factory().get_cinema_repository),
) -> list[MovieResponse]:
    movies = await cinema_repository.get_active_movies()
    return [MovieResponse.model_validate(movie) for movie in movies]


@movies_router.get("/popular")
async def get_popular_movies() -> list[dict]:
    """Top movies by paid tickets, precomputed by the Celery worker into Redis."""
    raw = await redis.get(POPULAR_KEY)
    if not raw:
        return []
    return json.loads(raw)


@movies_router.get("/shows/{movie_id}", response_model=list[ShowResponse])
async def get_shows_by_movie(
    movie_id: int,
    cinema_repository: CinemaRepository = Depends(Factory().get_cinema_repository),
) -> list[ShowResponse]:
    shows = await cinema_repository.get_shows_by_movie(movie_id=movie_id)
    return [ShowResponse.model_validate(show) for show in shows]


@movies_router.get("/{movie_id}", response_model=MovieResponse)
async def get_movie(
    movie_id: int,
    cinema_repository: CinemaRepository = Depends(Factory().get_cinema_repository),
) -> MovieResponse:
    """Movie details independent of whether it has scheduled shows."""
    movie = await cinema_repository.get_movie_by_id(movie_id)
    if movie is None:
        raise NotFoundException("Movie not found")
    return MovieResponse.model_validate(movie)
