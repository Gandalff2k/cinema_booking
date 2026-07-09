import asyncio
import json
import logging
from datetime import UTC, datetime, timedelta

import redis.asyncio as aioredis
from sqlalchemy import delete, func, select

from app.models import Movie, Order, OrderStatusEnum, Review, Show, Ticket
from core.config import config
from core.database import session, standalone_session
from worker import celery_app

logger = logging.getLogger(__name__)

RATING_KEY = "movie:{movie_id}:rating"
POPULAR_KEY = "movies:popular"
POPULAR_LIMIT = 10


def _redis_client() -> aioredis.Redis:
    # Fresh client per task run — the Celery worker uses a new event loop for
    # each asyncio.run(), so a module-level client would bind to a stale loop.
    return aioredis.from_url(config.REDIS_URL)


@standalone_session
async def _update_movie_rating(movie_id: int) -> None:
    query = select(func.avg(Review.rating), func.count(Review.id)).where(
        Review.movie_id == movie_id
    )
    avg_rating, reviews_count = (await session.execute(query)).one()

    payload = json.dumps(
        {
            "movie_id": movie_id,
            "avg_rating": round(float(avg_rating or 0.0), 2),
            "reviews_count": int(reviews_count or 0),
        }
    )

    redis = _redis_client()
    try:
        await redis.set(RATING_KEY.format(movie_id=movie_id), payload)
    finally:
        await redis.aclose()

    logger.info("Rating recalculated for movie %s: %s", movie_id, payload)


@standalone_session
async def _recalculate_popular_movies(limit: int) -> None:
    # Count only tickets that belong to PAID orders — real purchases.
    query = (
        select(Movie.id, Movie.title, func.count(Ticket.id).label("sold"))
        .join(Show, Show.movie_id == Movie.id)
        .join(Ticket, Ticket.show_id == Show.id)
        .join(Order, Order.id == Ticket.order_id)
        .where(Order.status == OrderStatusEnum.PAID)
        .group_by(Movie.id, Movie.title)
        .order_by(func.count(Ticket.id).desc())
        .limit(limit)
    )
    rows = (await session.execute(query)).all()

    data = json.dumps(
        [
            {"movie_id": movie_id, "title": title, "tickets_sold": int(sold)}
            for movie_id, title, sold in rows
        ]
    )

    redis = _redis_client()
    try:
        await redis.set(POPULAR_KEY, data)
    finally:
        await redis.aclose()

    logger.info("Popular movies recalculated (top %s)", limit)


@standalone_session
async def _release_stale_orders(minutes: int) -> None:
    """Cancel unpaid orders older than `minutes` and free their seats."""
    cutoff = datetime.now(UTC) - timedelta(minutes=minutes)
    result = await session.execute(
        select(Order)
        .where(Order.status == OrderStatusEnum.PENDING, Order.created_at < cutoff)
        .with_for_update()
    )
    stale = result.scalars().all()

    for order in stale:
        order.status = OrderStatusEnum.CANCELLED
        # Deleting the tickets releases the (show, seat) unique lock so the
        # seats become bookable again.
        await session.execute(delete(Ticket).where(Ticket.order_id == order.id))

    await session.commit()
    if stale:
        logger.info("Released %d stale unpaid order(s)", len(stale))


@celery_app.task(name="worker.tasks.cache_tasks.update_movie_rating")
def update_movie_rating_task(movie_id: int) -> None:
    asyncio.run(_update_movie_rating(movie_id))


@celery_app.task(name="worker.tasks.cache_tasks.release_stale_orders")
def release_stale_orders_task() -> None:
    asyncio.run(_release_stale_orders(config.STALE_ORDER_MINUTES))


@celery_app.task(name="worker.tasks.cache_tasks.recalculate_popular_movies")
def recalculate_popular_movies_task(limit: int = POPULAR_LIMIT) -> None:
    asyncio.run(_recalculate_popular_movies(limit))
