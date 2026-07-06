from typing import Callable

from fastapi import APIRouter, Depends

from app.controllers import AuthController, UserController
from app.models.domain import User
from app.schemas.extras.token import Token
from app.schemas.requests.users import LoginUserRequest, RegisterUserRequest
from app.schemas.responses.users import UserResponse
from core.factory import Factory
from core.fastapi.dependencies import AuthenticationRequired
from core.fastapi.dependencies.current_user import get_current_user
from core.fastapi.dependencies.current_user import get_current_admin

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from app.models import User, RoleEnum
from core.fastapi.dependencies.current_user import get_current_user

user_router = APIRouter()


class PasswordChangeRequest(BaseModel):
    old_password: str
    new_password: str


@user_router.get("/", dependencies=[Depends(AuthenticationRequired)])
async def get_users(
    user_controller: UserController = Depends(Factory().get_user_controller),
    assert_access: Callable = Depends(get_current_admin),
) -> list[UserResponse]:
    users = await user_controller.get_all()

    return users


@user_router.post("/", status_code=201)
async def register_user(
    register_user_request: RegisterUserRequest,
    auth_controller: AuthController = Depends(Factory().get_auth_controller),
) -> UserResponse:
    return await auth_controller.register(
        email=register_user_request.email,
        password=register_user_request.password,
        username=register_user_request.username,
    )


@user_router.post("/login")
async def login_user(
    login_user_request: LoginUserRequest,
    auth_controller: AuthController = Depends(Factory().get_auth_controller),
) -> Token:
    return await auth_controller.login(
        contact=login_user_request.contact, password=login_user_request.password
    )


@user_router.get("/me", dependencies=[Depends(AuthenticationRequired)])
def get_user(
    user: User = Depends(get_current_user),
) -> UserResponse:
    return user


@user_router.put("/me/password")
async def change_password(
    payload: PasswordChangeRequest, current_user: User = Depends(get_current_user)
):
    """Зміна пароля поточного користувача"""
    return {"message": "Password updated successfully"}


class ReviewCreateRequest(BaseModel):
    rating: int
    comment: str | None = None


class MovieCreateRequest(BaseModel):
    title: str
    description: str
    duration_minutes: int


def get_admin_user(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != RoleEnum.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions"
        )
    return current_user


movies_admin_router = APIRouter(prefix="/movies", tags=["Movies Admin"])


@movies_admin_router.post("", status_code=201)
async def create_movie(
    payload: MovieCreateRequest, admin: User = Depends(get_admin_user)
):
    """[АДМІН] Додавання нового фільму"""

    return {"message": "Movie created", "movie_id": 999}


@movies_admin_router.put("/{movie_id}")
async def update_movie(
    movie_id: int, payload: MovieCreateRequest, admin: User = Depends(get_admin_user)
):
    """[АДМІН] Редагування існуючого фільму"""
    return {"message": f"Movie {movie_id} updated"}


@movies_admin_router.delete("/{movie_id}")
async def delete_movie(movie_id: int, admin: User = Depends(get_admin_user)):
    """[АДМІН] Видалення фільму"""
    return {"message": f"Movie {movie_id} deleted"}


reviews_router = APIRouter(prefix="/reviews", tags=["Reviews"])


@reviews_router.post("/movies/{movie_id}")
async def add_review(
    movie_id: int,
    payload: ReviewCreateRequest,
    current_user: User = Depends(get_current_user),
):
    """Додавання відгуку на фільм"""
    # 1. Збереження відгуку в БД (INSERT INTO reviews)

    # 2. ТРИГЕР ФОНОВОЇ ЗАДАЧІ ДЛЯ КЕШУ:
    # recalculate_movie_rating_task.delay(movie_id)

    return {"message": "Review added successfully"}


@reviews_router.delete("/{review_id}")
async def delete_review(review_id: int, admin: User = Depends(get_admin_user)):
    """[АДМІН] Видалення будь-якого відгуку"""
    # 1. Видалення з БД
    # 2. recalculate_movie_rating_task.delay(movie_id)
    return {"message": f"Review {review_id} deleted"}
