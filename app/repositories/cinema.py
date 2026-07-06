from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import joinedload, selectinload

from app.models import Cinema, Hall, Movie, Show
from core.repository import BaseRepository


class CinemaRepository(BaseRepository[Movie]):
    """
    Cinema repository provides movie and show read operations.
    """

    async def get_active_movies(self) -> Sequence[Movie]:
        query = (
            select(Movie)
            .options(selectinload(Movie.genres))
            .where(Movie.is_active.is_(True))
            .order_by(Movie.release_date.desc().nullslast(), Movie.title.asc())
        )
        result = await self.session.scalars(query)
        return result.all()

    async def get_shows_by_movie(self, movie_id: int) -> Sequence[Show]:
        query = (
            select(Show)
            .join(Show.hall)
            .join(Hall.cinema)
            .options(joinedload(Show.movie).selectinload(Movie.genres))
            .where(Show.movie_id == movie_id)
            .order_by(Show.start_time.asc())
        )
        result = await self.session.execute(query)
        return result.unique().scalars().all()
