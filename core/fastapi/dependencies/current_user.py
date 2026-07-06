from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.controllers.user import UserController
from app.models.domain import RoleEnum, User
from core.exceptions import CustomException, NotFoundException
from core.factory import Factory
from core.security.jwt import decode_token


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/v1/auth/login")


def _unauthorized(detail: str = "Invalid or expired token") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    user_controller: UserController = Depends(Factory().get_user_controller),
) -> User:
    try:
        payload = decode_token(token)
        if payload.get("type") not in {"access", None}:
            raise _unauthorized()

        user_uuid = UUID(str(payload.get("sub")))
        return await user_controller.get_by_uuid(user_uuid)
    except (CustomException, TypeError, ValueError, NotFoundException):
        raise _unauthorized() from None


async def get_current_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    if current_user.role != RoleEnum.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )

    return current_user
