from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr

from app.models.domain import RoleEnum


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    uuid: UUID
    email: EmailStr
    username: str
    role: RoleEnum


class TokenResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    access_token: str
    refresh_token: str
    token_type: Literal["bearer"] = "bearer"
