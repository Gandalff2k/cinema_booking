from typing import Annotated

from pydantic import BaseModel, EmailStr, Field, StringConstraints


PhoneNumber = Annotated[str, StringConstraints(pattern=r"^\+?[1-9]\d{7,14}$")]


class RegisterRequest(BaseModel):
    email: EmailStr
    phone_number: PhoneNumber = Field(
        ..., description="Phone number in E.164-like format"
    )
    password: Annotated[str, StringConstraints(min_length=8, max_length=64)]
    username: Annotated[str, StringConstraints(min_length=3, max_length=64)]


class LoginRequest(BaseModel):
    email: EmailStr
    password: Annotated[str, StringConstraints(min_length=1)]
