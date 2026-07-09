from collections.abc import Callable

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.controllers import UserController
from app.models import RoleEnum, User
from app.repositories import ReviewRepository
from app.schemas.responses.users import UserResponse
from core.database import Propagation, Transactional
from core.exceptions import BadRequestException, NotFoundException
from core.factory import Factory
from core.fastapi.dependencies.current_user import get_current_admin, get_current_user
from core.security.password import get_password_hash, verify_password
from worker.tasks.cache_tasks import update_movie_rating_task

user_router = APIRouter()


class PasswordChangeRequest(BaseModel):
    old_password: str
    new_password: str


@user_router.get("/")
async def get_users(
    user_controller: UserController = Depends(Factory().get_user_controller),
    assert_access: Callable = Depends(get_current_admin),
) -> list[UserResponse]:
    users = await user_controller.get_all()

    return users


@user_router.put("/me/password")
@Transactional(propagation=Propagation.REQUIRED)
async def change_password(
    payload: PasswordChangeRequest, current_user: User = Depends(get_current_user)
):
    if not verify_password(payload.old_password, current_user.password):
        raise BadRequestException("Current password is incorrect")
    if len(payload.new_password) < 8:
        raise BadRequestException("New password must be at least 8 characters")

    current_user.password = get_password_hash(payload.new_password)
    return {"message": "Password updated"}


class ReviewCreateRequest(BaseModel):
    rating: int = Field(ge=1, le=10)
    comment: str | None = Field(default=None, max_length=2000)


class ReviewResponse(BaseModel):
    id: int
    user_id: int
    movie_id: int
    rating: int
    comment: str | None


class ReviewItem(BaseModel):
    id: int
    username: str
    rating: int
    comment: str | None


class MovieReviewsResponse(BaseModel):
    average: float
    count: int
    distribution: dict[int, int]
    reviews: list[ReviewItem]


def get_admin_user(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != RoleEnum.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions"
        )
    return current_user


reviews_router = APIRouter(prefix="/reviews", tags=["Reviews"])


def _to_review_item(review) -> "ReviewItem":
    return ReviewItem(
        id=review.id,
        username=review.user.username if review.user else "Guest",
        rating=review.rating,
        comment=review.comment,
    )


@reviews_router.get("/movies/{movie_id}", response_model=MovieReviewsResponse)
async def get_movie_reviews(
    movie_id: int,
    review_repository: ReviewRepository = Depends(Factory().get_review_repository),
) -> MovieReviewsResponse:
    average, count, distribution = await review_repository.get_stats_for_movie(movie_id)
    sample = await review_repository.get_sample_for_movie(movie_id, offset=0, limit=6)
    return MovieReviewsResponse(
        average=average,
        count=count,
        distribution=distribution,
        reviews=[_to_review_item(r) for r in sample],
    )


@reviews_router.get("/movies/{movie_id}/list", response_model=list[ReviewItem])
async def list_movie_reviews(
    movie_id: int,
    offset: int = 0,
    limit: int = 6,
    review_repository: ReviewRepository = Depends(Factory().get_review_repository),
) -> list[ReviewItem]:
    limit = max(1, min(limit, 30))
    reviews = await review_repository.get_sample_for_movie(
        movie_id, offset=max(0, offset), limit=limit
    )
    return [_to_review_item(r) for r in reviews]


@reviews_router.post(
    "/movies/{movie_id}", response_model=ReviewResponse, status_code=201
)
@Transactional(propagation=Propagation.REQUIRED)
async def add_review(
    movie_id: int,
    payload: ReviewCreateRequest,
    current_user: User = Depends(get_current_user),
    review_repository: ReviewRepository = Depends(Factory().get_review_repository),
) -> ReviewResponse:
    existing = await review_repository.get_by_user_and_movie(
        user_id=current_user.id, movie_id=movie_id
    )
    if existing is not None:
        raise BadRequestException("You have already reviewed this movie")

    review = await review_repository.create(
        user_id=current_user.id,
        movie_id=movie_id,
        rating=payload.rating,
        comment=payload.comment,
    )

    update_movie_rating_task.apply_async(args=[movie_id], countdown=3)

    return ReviewResponse.model_validate(review, from_attributes=True)


@reviews_router.delete("/{review_id}")
@Transactional(propagation=Propagation.REQUIRED)
async def delete_review(
    review_id: int,
    admin: User = Depends(get_admin_user),
    review_repository: ReviewRepository = Depends(Factory().get_review_repository),
):
    review = await review_repository.get_by_id(review_id)
    if review is None:
        raise NotFoundException("Review not found")

    movie_id = review.movie_id
    await review_repository.delete_review(review)

    update_movie_rating_task.apply_async(args=[movie_id], countdown=3)
    return {"message": f"Review {review_id} deleted"}
