# pylint: disable=all

import re

from typing import Annotated

from pydantic import BaseModel, EmailStr, Field, validator


class RegisterUserRequest(BaseModel):
    email: EmailStr
    password: Annotated[str, Field(min_length=8, max_length=64)]
    username: Annotated[str, Field(min_length=3, max_length=64)]

    @validator("password")
    def password_must_contain_special_characters(cls, v):
        if not re.search(r"[^a-zA-Z0-9]", v):
            raise ValueError("Password must contain special characters")
        return v

    @validator("password")
    def password_must_contain_numbers(cls, v):
        if not re.search(r"[0-9]", v):
            raise ValueError("Password must contain numbers")
        return v

    @validator("password")
    def password_must_contain_uppercase(cls, v):
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain uppercase characters")
        return v

    @validator("password")
    def password_must_contain_lowercase(cls, v):
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain lowercase characters")
        return v

    @validator("username")
    def username_must_not_contain_special_characters(cls, v):
        if re.search(r"[^a-zA-Z0-9]", v):
            raise ValueError("Username must not contain special characters")
        return v


class LoginUserRequest(BaseModel):
    contact: str
    password: str
