from typing import Optional, Tuple
from uuid import UUID

from starlette.authentication import AuthenticationBackend
from starlette.middleware.authentication import (
    AuthenticationMiddleware as BaseAuthenticationMiddleware,
)
from starlette.requests import HTTPConnection

from app.schemas.extras.current_user import CurrentUser
from core.security.jwt import decode_token


class AuthBackend(AuthenticationBackend):
    async def authenticate(
        self, conn: HTTPConnection
    ) -> Tuple[bool, Optional[CurrentUser]]:
        current_user = CurrentUser()
        authorization: str = conn.headers.get("Authorization")
        if not authorization:
            return False, current_user

        try:
            scheme, token = authorization.split(" ")
            if scheme.lower() != "bearer":
                return False, current_user
        except ValueError:
            return False, current_user

        if not token:
            return False, current_user

        try:
            payload = decode_token(token)
            token_type = payload.get("type")
            if token_type not in {"access", None}:
                return False, current_user

            user_uuid = UUID(str(payload.get("sub")))
        except (TypeError, ValueError):
            return False, current_user
        except Exception:
            return False, current_user

        current_user.uuid = user_uuid
        return True, current_user


class AuthenticationMiddleware(BaseAuthenticationMiddleware):
    pass
