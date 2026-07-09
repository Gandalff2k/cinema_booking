import re
from typing import Annotated

from pydantic import BaseModel, EmailStr, Field, field_validator


class RegisterUserRequest(BaseModel):
    email: EmailStr
    password: Annotated[str, Field(min_length=8, max_length=64)]
    username: Annotated[str, Field(min_length=3, max_length=64)]

    @field_validator("username")
    @classmethod
    def username_must_not_contain_special_characters(cls, v: str) -> str:
        if re.search(r"[^a-zA-Z0-9_]", v):
            raise ValueError("Username may only contain letters, digits and _")
        return v


class LoginUserRequest(BaseModel):
    contact: str
    password: str
