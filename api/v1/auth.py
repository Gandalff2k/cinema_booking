from fastapi import APIRouter, Depends

from app.controllers import AuthController
from app.models import User
from app.schemas.extras.token import Token
from app.schemas.requests.users import LoginUserRequest, RegisterUserRequest
from app.schemas.responses.users import TokenResponse, UserResponse
from core.factory import Factory
from core.fastapi.dependencies.current_user import get_current_user
from core.fastapi.dependencies.rate_limiter import RateLimiter

auth_router = APIRouter(prefix="/auth", tags=["Auth"])


@auth_router.post(
    "/register",
    response_model=UserResponse,
    status_code=201,
    dependencies=[Depends(RateLimiter())],
)
async def register(
    payload: RegisterUserRequest,
    auth_controller: AuthController = Depends(Factory().get_auth_controller),
) -> UserResponse:
    return await auth_controller.register(
        email=payload.email,
        password=payload.password,
        username=payload.username,
    )


@auth_router.post(
    "/login",
    response_model=TokenResponse,
    dependencies=[Depends(RateLimiter())],
)
async def login(
    payload: LoginUserRequest,
    auth_controller: AuthController = Depends(Factory().get_auth_controller),
) -> Token:
    return await auth_controller.login(
        contact=payload.contact, password=payload.password
    )


@auth_router.get("/me", response_model=UserResponse)
async def me(current_user: User = Depends(get_current_user)) -> UserResponse:
    return current_user
