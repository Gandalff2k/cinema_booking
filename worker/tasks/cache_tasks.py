import json
from worker import celery_app
from core.database import standalone_session, session
from sqlalchemy import select, func
from app.models import Review
# import redis_client (твій клієнт з core/cache)


@standalone_session
async def _update_movie_rating_in_redis(movie_id: int):
    # 1. Рахуємо новий середній бал у базі
    query = select(func.avg(Review.rating)).where(Review.movie_id == movie_id)
    result = await session.execute(query)
    new_avg = result.scalar() or 0.0

    # 2. Записуємо в Redis
    redis_key = f"movie:{movie_id}:rating"
    # await redis_client.set(redis_key, round(new_avg, 1))
    print(f" [DEBUG] Рейтинг фільму {movie_id} оновлено в кеші: {new_avg}")


@celery_app.task(name="worker.tasks.cache_tasks.update_movie_rating")
def update_movie_rating_task(movie_id: int):
    import asyncio

    asyncio.run(_update_movie_rating_in_redis(movie_id))
