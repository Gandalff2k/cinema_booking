from typing import cast
from uuid import UUID

from pydantic import EmailStr

from app.models import User
from app.repositories import UserRepository
from app.schemas.extras.token import Token
from core.controller import BaseController
from core.database import Propagation, Transactional
from core.exceptions import BadRequestException, UnauthorizedException
from core.security.jwt import create_access_token, create_refresh_token, decode_token
from core.security.password import get_password_hash, verify_password


class AuthController(BaseController[User]):
    def __init__(self, user_repository: UserRepository):
        super().__init__(model=User, repository=user_repository)
        self.user_repository = user_repository

    @Transactional(propagation=Propagation.REQUIRED)
    async def register(self, email: EmailStr, password: str, username: str) -> User:
        user = await self.user_repository.get_by_email(email)

        if user:
            raise BadRequestException("User already exists with this email")

        user = await self.user_repository.get_by_username(username)

        if user:
            raise BadRequestException("User already exists with this username")

        password = get_password_hash(password)

        return await self.user_repository.create(
            {
                "email": email,
                "password": password,
                "username": username,
            }
        )

    async def login(self, contact: str, password: str) -> Token:
        user = await self.user_repository.get_by_contact(contact)

        if not user:
            raise BadRequestException("Invalid credentials")

        if not verify_password(password, cast(str, user.password)):
            raise BadRequestException("Invalid credentials")

        return Token(
            access_token=create_access_token(cast(UUID, user.uuid)),
            refresh_token=create_refresh_token(cast(UUID, user.uuid)),
        )

    async def refresh_token(self, access_token: str, refresh_token: str) -> Token:
        if access_token:
            decode_token(access_token, verify_exp=False)

        refresh_payload = decode_token(refresh_token)
        if refresh_payload.get("type") != "refresh":
            raise UnauthorizedException("Invalid refresh token")

        user_uuid = refresh_payload.get("sub")
        if not user_uuid:
            raise UnauthorizedException("Invalid refresh token")

        return Token(
            access_token=create_access_token(user_uuid),
            refresh_token=create_refresh_token(user_uuid),
        )
