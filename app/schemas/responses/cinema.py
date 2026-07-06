from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.domain import FormatEnum, SeatTypeEnum


class GenreResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class MovieResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str | None = None
    poster_url: str | None = None
    trailer_url: str | None = None
    duration_minutes: int = Field(..., gt=0)
    age_rating: str | None = None
    release_date: date | None = None
    is_active: bool
    genres: list[GenreResponse] = Field(default_factory=list)


class ShowResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    start_time: datetime
    base_price: Decimal
    format: FormatEnum
    movie: MovieResponse


class SeatResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    row_number: int
    seat_number: int
    seat_type: SeatTypeEnum
    price_multiplier: Decimal
    is_occupied: bool = False
