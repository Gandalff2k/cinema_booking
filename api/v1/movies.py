from collections.abc import Sequence

from fastapi import APIRouter, Depends

from app.models import Movie, Show
from app.repositories import CinemaRepository
from app.schemas.responses.cinema import MovieResponse, ShowResponse
from core.cache import Cache
from core.factory import Factory

movies_router = APIRouter(prefix="/movies", tags=["Movies"])


@movies_router.get("", response_model=list[MovieResponse])
@Cache.cached(prefix="movies", ttl=900)
async def get_movies(
    cinema_repository: CinemaRepository = Depends(Factory().get_cinema_repository),
) -> list[MovieResponse]:
    movies = await cinema_repository.get_active_movies()
    return [MovieResponse.model_validate(movie) for movie in movies]


@movies_router.get("/shows/{movie_id}", response_model=list[ShowResponse])
async def get_shows_by_movie(
    movie_id: int,
    cinema_repository: CinemaRepository = Depends(Factory().get_cinema_repository),
) -> list[ShowResponse]:
    shows = await cinema_repository.get_shows_by_movie(movie_id=movie_id)
    return [ShowResponse.model_validate(show) for show in shows]
