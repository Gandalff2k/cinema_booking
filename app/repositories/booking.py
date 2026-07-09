from collections.abc import Sequence

from sqlalchemy import and_, select
from sqlalchemy.orm import contains_eager

from app.models import Hall, Promocode, Seat, Show, Ticket
from core.repository import BaseRepository


class BookingRepository(BaseRepository[Seat]):
    async def lock_seats_for_update(
        self, show_id: int, seat_ids: list[int]
    ) -> Sequence[Seat]:
        query = (
            select(Seat)
            .join(Seat.hall)
            .join(Hall.cinema)
            .join(Show, Show.hall_id == Hall.id)
            .where(Show.id == show_id, Seat.id.in_(seat_ids))
            .options(contains_eager(Seat.hall).contains_eager(Hall.cinema))
            .with_for_update()
        )
        result = await self.session.execute(query)
        return result.unique().scalars().all()

    async def get_show_by_id(self, show_id: int) -> Show | None:
        query = select(Show).where(Show.id == show_id)
        result = await self.session.scalars(query)
        return result.one_or_none()

    async def get_existing_tickets(
        self, show_id: int, seat_ids: list[int]
    ) -> Sequence[Ticket]:
        query = select(Ticket).where(
            Ticket.show_id == show_id,
            Ticket.seat_id.in_(seat_ids),
        )
        result = await self.session.scalars(query)
        return result.all()

    async def get_promocode(self, promocode_id: int) -> Promocode | None:
        query = select(Promocode).where(Promocode.id == promocode_id)
        result = await self.session.scalars(query)
        return result.one_or_none()

    async def get_seats_for_show(
        self, show_id: int
    ) -> Sequence[tuple[Seat, int | None]]:
        query = (
            select(Seat, Ticket.id)
            .join(Hall, Seat.hall_id == Hall.id)
            .join(Show, Show.hall_id == Hall.id)
            .outerjoin(
                Ticket,
                and_(Ticket.show_id == Show.id, Ticket.seat_id == Seat.id),
            )
            .where(Show.id == show_id)
            .order_by(Seat.row_number.asc(), Seat.seat_number.asc())
        )
        result = await self.session.execute(query)
        return result.all()
