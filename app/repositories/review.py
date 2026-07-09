from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.orm import joinedload

from app.models import Review
from core.repository import BaseRepository


class ReviewRepository(BaseRepository[Review]):
    async def get_by_user_and_movie(self, user_id: int, movie_id: int) -> Review | None:
        query = select(Review).where(
            Review.user_id == user_id, Review.movie_id == movie_id
        )
        result = await self.session.scalars(query)
        return result.one_or_none()

    async def get_sample_for_movie(
        self, movie_id: int, offset: int = 0, limit: int = 6
    ) -> Sequence[Review]:
        query = (
            select(Review)
            .options(joinedload(Review.user))
            .where(Review.movie_id == movie_id)
            .order_by(Review.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.scalars(query)
        return result.all()

    async def get_stats_for_movie(
        self, movie_id: int
    ) -> tuple[float, int, dict[int, int]]:
        agg = await self.session.execute(
            select(func.avg(Review.rating), func.count(Review.id)).where(
                Review.movie_id == movie_id
            )
        )
        avg_rating, count = agg.one()

        dist_rows = await self.session.execute(
            select(Review.rating, func.count(Review.id))
            .where(Review.movie_id == movie_id)
            .group_by(Review.rating)
        )
        distribution = {int(rating): int(n) for rating, n in dist_rows.all()}

        return round(float(avg_rating or 0.0), 1), int(count or 0), distribution

    async def get_by_id(self, review_id: int) -> Review | None:
        query = select(Review).where(Review.id == review_id)
        result = await self.session.scalars(query)
        return result.one_or_none()

    async def create(
        self, user_id: int, movie_id: int, rating: int, comment: str | None
    ) -> Review:
        review = Review(
            user_id=user_id,
            movie_id=movie_id,
            rating=rating,
            comment=comment,
        )
        self.session.add(review)
        await self.session.flush()
        return review

    async def delete_review(self, review: Review) -> None:
        await self.session.delete(review)
        await self.session.flush()
