import asyncio
import logging
from uuid import uuid4

import stripe
from fastapi import APIRouter, Depends, File, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import selectinload

from app.integrations.minio_client import upload_poster
from app.models import (
    Genre,
    Movie,
    Order,
    OrderStatusEnum,
    Review,
    Ticket,
    Transaction,
    TransactionStatusEnum,
    User,
)
from core.cache import Cache
from core.config import config
from core.database import Propagation, Transactional, session
from core.exceptions import BadRequestException, NotFoundException
from core.fastapi.dependencies.current_user import get_current_admin
from worker.tasks.cache_tasks import (
    recalculate_popular_movies_task,
    update_movie_rating_task,
)

logger = logging.getLogger(__name__)

admin_router = APIRouter(
    prefix="/admin",
    tags=["Admin"],
    dependencies=[Depends(get_current_admin)],
)


class MovieCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    poster_url: str | None = None
    duration_minutes: int = Field(gt=0)
    age_rating: str | None = None


class MovieUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    poster_url: str | None = None
    duration_minutes: int | None = Field(default=None, gt=0)
    age_rating: str | None = None
    is_active: bool | None = None


class AdminMovieResponse(BaseModel):
    id: int
    title: str
    poster_url: str | None
    duration_minutes: int
    age_rating: str | None
    is_active: bool
    genres: list[str] = []


class AdminStatsResponse(BaseModel):
    movies: int
    active_movies: int
    users: int
    reviews: int
    avg_rating: float
    orders: int
    paid_orders: int
    pending_orders: int
    refunded_orders: int
    revenue: float


@admin_router.get("/stats", response_model=AdminStatsResponse)
async def admin_stats() -> AdminStatsResponse:
    async def count(model, *where):
        return await session.scalar(select(func.count(model.id)).where(*where)) or 0

    revenue = await session.scalar(
        select(func.coalesce(func.sum(Order.total_price), 0)).where(
            Order.status == OrderStatusEnum.PAID
        )
    )
    avg_rating = await session.scalar(select(func.avg(Review.rating)))
    return AdminStatsResponse(
        movies=await count(Movie),
        active_movies=await count(Movie, Movie.is_active.is_(True)),
        users=await count(User),
        reviews=await count(Review),
        avg_rating=round(float(avg_rating or 0), 1),
        orders=await count(Order),
        paid_orders=await count(Order, Order.status == OrderStatusEnum.PAID),
        pending_orders=await count(Order, Order.status == OrderStatusEnum.PENDING),
        refunded_orders=await count(Order, Order.status == OrderStatusEnum.REFUNDED),
        revenue=float(revenue or 0),
    )


@admin_router.get("/genres")
async def admin_genres() -> list[dict]:
    rows = await session.scalars(select(Genre).order_by(Genre.name))
    return [{"id": g.id, "name": g.name} for g in rows]


@admin_router.get("/movies", response_model=list[AdminMovieResponse])
async def admin_list_movies(
    search: str | None = None,
    genre_id: int | None = None,
    offset: int = 0,
    limit: int = 10,
) -> list[AdminMovieResponse]:
    query = select(Movie).options(selectinload(Movie.genres)).order_by(Movie.id.desc())
    if search:
        query = query.where(Movie.title.ilike(f"%{search}%"))
    if genre_id:
        query = query.join(Movie.genres).where(Genre.id == genre_id)

    query = query.offset(max(0, offset)).limit(max(1, min(limit, 50)))
    result = await session.scalars(query)
    return [
        AdminMovieResponse(
            id=m.id,
            title=m.title,
            poster_url=m.poster_url,
            duration_minutes=m.duration_minutes,
            age_rating=m.age_rating,
            is_active=m.is_active,
            genres=[g.name for g in m.genres],
        )
        for m in result.unique()
    ]


def _movie_response(
    movie: Movie, genres: list[str] | None = None
) -> AdminMovieResponse:

    return AdminMovieResponse(
        id=movie.id,
        title=movie.title,
        poster_url=movie.poster_url,
        duration_minutes=movie.duration_minutes,
        age_rating=movie.age_rating,
        is_active=movie.is_active,
        genres=genres or [],
    )


@admin_router.post("/movies", response_model=AdminMovieResponse, status_code=201)
@Transactional(propagation=Propagation.REQUIRED)
async def admin_create_movie(payload: MovieCreateRequest) -> AdminMovieResponse:
    movie = Movie(**payload.model_dump())
    session.add(movie)
    await session.flush()
    await Cache.remove_by_prefix("movies")
    return _movie_response(movie)


@admin_router.put("/movies/{movie_id}", response_model=AdminMovieResponse)
@Transactional(propagation=Propagation.REQUIRED)
async def admin_update_movie(
    movie_id: int, payload: MovieUpdateRequest
) -> AdminMovieResponse:
    movie = await session.get(Movie, movie_id)
    if movie is None:
        raise NotFoundException("Movie not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(movie, field, value)

    await session.flush()
    await Cache.remove_by_prefix("movies")
    return _movie_response(movie)


_POSTER_TYPES = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}
_MAX_POSTER_BYTES = 5 * 1024 * 1024


@admin_router.post("/movies/{movie_id}/poster")
@Transactional(propagation=Propagation.REQUIRED)
async def admin_upload_poster(
    movie_id: int, file: UploadFile = File(...)
) -> dict[str, str]:
    movie = await session.get(Movie, movie_id)
    if movie is None:
        raise NotFoundException("Movie not found")
    if file.content_type not in _POSTER_TYPES:
        raise BadRequestException("Only JPEG, PNG or WEBP images are allowed")

    data = await file.read()
    if len(data) > _MAX_POSTER_BYTES:
        raise BadRequestException("Image is too large (max 5 MB)")

    object_name = f"{uuid4().hex}.{_POSTER_TYPES[file.content_type]}"
    poster_url = await asyncio.to_thread(
        upload_poster, object_name, data, file.content_type
    )
    movie.poster_url = poster_url
    await session.flush()
    await Cache.remove_by_prefix("movies")
    return {"message": "Poster updated", "poster_url": poster_url}


@admin_router.delete("/movies/{movie_id}")
@Transactional(propagation=Propagation.REQUIRED)
async def admin_delete_movie(movie_id: int) -> dict[str, str]:
    movie = await session.get(Movie, movie_id)
    if movie is None:
        raise NotFoundException("Movie not found")

    movie.is_active = False
    await session.flush()
    await Cache.remove_by_prefix("movies")
    return {"message": f"Movie {movie_id} deactivated"}


class AdminReviewResponse(BaseModel):
    id: int
    movie_id: int
    movie_title: str
    user_id: int
    rating: int
    comment: str | None


@admin_router.get("/reviews", response_model=list[AdminReviewResponse])
async def admin_list_reviews(
    search: str | None = None, offset: int = 0, limit: int = 10
) -> list[AdminReviewResponse]:
    query = select(Review).options(selectinload(Review.movie))
    if search:
        query = query.join(Review.movie).where(
            or_(
                Review.comment.ilike(f"%{search}%"),
                Movie.title.ilike(f"%{search}%"),
            )
        )
    query = (
        query.order_by(Review.created_at.desc())
        .offset(max(0, offset))
        .limit(max(1, min(limit, 50)))
    )
    reviews = await session.scalars(query)
    return [
        AdminReviewResponse(
            id=r.id,
            movie_id=r.movie_id,
            movie_title=r.movie.title,
            user_id=r.user_id,
            rating=r.rating,
            comment=r.comment,
        )
        for r in reviews
    ]


@admin_router.delete("/reviews/{review_id}")
@Transactional(propagation=Propagation.REQUIRED)
async def admin_delete_review(review_id: int) -> dict[str, str]:
    review = await session.get(Review, review_id)
    if review is None:
        raise NotFoundException("Review not found")

    movie_id = review.movie_id
    await session.delete(review)
    await session.flush()

    update_movie_rating_task.apply_async(args=[movie_id], countdown=3)
    return {"message": f"Review {review_id} deleted"}


class AdminOrderResponse(BaseModel):
    id: int
    user_email: str | None
    total_price: float
    status: str
    tickets_count: int


@admin_router.get("/orders", response_model=list[AdminOrderResponse])
async def admin_list_orders(
    email: str | None = None, offset: int = 0, limit: int = 10
) -> list[AdminOrderResponse]:
    query = (
        select(Order, User.email, func.count(Ticket.id))
        .join(User, User.id == Order.user_id, isouter=True)
        .join(Ticket, Ticket.order_id == Order.id, isouter=True)
    )
    if email:
        query = query.where(User.email.ilike(f"%{email}%"))
    query = (
        query.group_by(Order.id, User.email)
        .order_by(Order.created_at.desc())
        .offset(max(0, offset))
        .limit(max(1, min(limit, 50)))
    )
    rows = (await session.execute(query)).all()
    return [
        AdminOrderResponse(
            id=order.id,
            user_email=email,
            total_price=float(order.total_price),
            status=order.status.value,
            tickets_count=int(tickets_count),
        )
        for order, email, tickets_count in rows
    ]


@admin_router.post("/orders/{order_id}/refund")
@Transactional(propagation=Propagation.REQUIRED)
async def admin_refund_order(order_id: int) -> dict[str, str | bool]:
    order = await session.get(Order, order_id)
    if order is None:
        raise NotFoundException("Order not found")
    if order.status != OrderStatusEnum.PAID:
        raise BadRequestException("Only paid orders can be refunded")

    transaction = await session.scalar(
        select(Transaction)
        .where(
            Transaction.order_id == order.id,
            Transaction.status == TransactionStatusEnum.SUCCESS,
        )
        .order_by(Transaction.id.desc())
    )

    refunded_via_stripe = False
    if transaction and transaction.provider_payment_id and config.STRIPE_SECRET_KEY:
        try:
            stripe.api_key = config.STRIPE_SECRET_KEY
            await stripe.Refund.create_async(
                payment_intent=transaction.provider_payment_id
            )
            refunded_via_stripe = True
        except Exception:
            logger.exception("Stripe refund failed for order %s", order_id)

    order.status = OrderStatusEnum.REFUNDED
    await session.execute(delete(Ticket).where(Ticket.order_id == order.id))
    await session.flush()

    recalculate_popular_movies_task.delay()

    return {
        "message": f"Order {order_id} refunded",
        "stripe_refund": refunded_via_stripe,
    }
