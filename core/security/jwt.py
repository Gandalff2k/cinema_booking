from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import jwt

from core.config import config
from core.exceptions import CustomException

ACCESS_TOKEN_TTL = timedelta(minutes=15)
REFRESH_TOKEN_TTL = timedelta(days=30)


class JWTDecodeError(CustomException):
    code = 401
    message = "Invalid token"


class JWTExpiredError(CustomException):
    code = 401
    message = "Token expired"


def _encode_token(subject: str, expires_delta: timedelta, token_type: str) -> str:
    now = datetime.now(tz=UTC)
    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
    }
    return jwt.encode(payload, config.SECRET_KEY, algorithm=config.JWT_ALGORITHM)


def create_access_token(user_uuid: UUID | str) -> str:
    return _encode_token(str(user_uuid), ACCESS_TOKEN_TTL, "access")


def create_refresh_token(user_uuid: UUID | str) -> str:
    return _encode_token(str(user_uuid), REFRESH_TOKEN_TTL, "refresh")


def decode_token(token: str, *, verify_exp: bool = True) -> dict[str, Any]:
    try:
        return jwt.decode(
            token,
            config.SECRET_KEY,
            algorithms=[config.JWT_ALGORITHM],
            options={"verify_exp": verify_exp},
        )
    except jwt.ExpiredSignatureError as exception:
        raise JWTExpiredError() from exception
    except jwt.PyJWTError as exception:
        raise JWTDecodeError() from exception


class JWTHandler:
    secret_key = config.SECRET_KEY
    algorithm = config.JWT_ALGORITHM
    access_token_ttl = ACCESS_TOKEN_TTL
    refresh_token_ttl = REFRESH_TOKEN_TTL

    @staticmethod
    def encode(payload: dict[str, Any]) -> str:
        subject = str(payload.get("sub", ""))
        token_type = str(payload.get("type", "access"))
        expires_delta = (
            JWTHandler.refresh_token_ttl
            if token_type == "refresh"
            else JWTHandler.access_token_ttl
        )
        return _encode_token(
            subject=subject, expires_delta=expires_delta, token_type=token_type
        )

    @staticmethod
    def decode(token: str) -> dict[str, Any]:
        return decode_token(token)

    @staticmethod
    def decode_expired(token: str) -> dict[str, Any]:
        return decode_token(token, verify_exp=False)
