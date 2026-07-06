from uuid import UUID

from pydantic import BaseModel, Field


class CurrentUser(BaseModel):
    id: int | None = Field(default=None, description="User ID")
    uuid: UUID | None = Field(default=None, description="User UUID")

    class Config:
        validate_assignment = True
