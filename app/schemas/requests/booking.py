from typing import Annotated

from pydantic import BaseModel, Field


class CreateOrderRequest(BaseModel):
    seat_ids: Annotated[list[int], Field(min_length=1)]
    show_id: int = Field(..., gt=0)
    promocode_id: int | None = Field(default=None, gt=0)
