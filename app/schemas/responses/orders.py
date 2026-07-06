from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.domain import OrderStatusEnum


class OrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int | None = None
    promocode_id: int | None = None
    idempotency_key: UUID
    total_price: Decimal = Field(..., ge=0)
    status: OrderStatusEnum
    created_at: datetime
    ticket_ids: list[int] = Field(default_factory=list)
    checkout_url: str | None = None
