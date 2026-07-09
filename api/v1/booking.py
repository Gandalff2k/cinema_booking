from datetime import datetime
from decimal import Decimal
from uuid import uuid4

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.integrations.stripe_pay import create_checkout_session
from app.models import Order, OrderStatusEnum, Seat, Show, Ticket, User
from app.repositories import BookingRepository
from app.schemas.requests.booking import CreateOrderRequest
from app.schemas.responses.cinema import SeatResponse
from app.schemas.responses.orders import OrderResponse
from core.database import Propagation, Transactional, session
from core.exceptions import BadRequestException, NotFoundException
from core.factory import Factory
from core.fastapi.dependencies.current_user import get_current_user
from core.fastapi.dependencies.rate_limiter import RateLimiter


class TicketDetailResponse(BaseModel):
    ticket_id: int
    movie_title: str
    hall_name: str
    start_time: datetime
    row: int
    seat: int
    price: Decimal
    qr_code: str | None


class MyOrderDetailedResponse(BaseModel):
    id: int
    total_price: Decimal
    created_at: datetime
    status: str
    tickets: list[TicketDetailResponse]


booking_router = APIRouter(prefix="/booking", tags=["Booking"])


@booking_router.get("/shows/{show_id}/seats", response_model=list[SeatResponse])
async def get_show_seats(
    show_id: int,
    booking_repository: BookingRepository = Depends(Factory().get_booking_repository),
) -> list[SeatResponse]:
    seat_rows = await booking_repository.get_seats_for_show(show_id)
    return [
        SeatResponse(
            id=seat.id,
            row_number=seat.row_number,
            seat_number=seat.seat_number,
            seat_type=seat.seat_type,
            price_multiplier=seat.price_multiplier,
            is_occupied=ticket_id is not None,
        )
        for seat, ticket_id in seat_rows
    ]


@booking_router.post(
    "/orders",
    response_model=OrderResponse,
    status_code=201,
    dependencies=[Depends(RateLimiter())],
)
@Transactional(propagation=Propagation.REQUIRED)
async def create_order(
    payload: CreateOrderRequest,
    current_user: User = Depends(get_current_user),
    booking_repository: BookingRepository = Depends(Factory().get_booking_repository),
) -> OrderResponse:
    if len(payload.seat_ids) != len(set(payload.seat_ids)):
        raise BadRequestException("Duplicate seat ids are not allowed")

    show = await booking_repository.get_show_by_id(payload.show_id)
    if not show:
        raise NotFoundException("Show not found")
    locked_seats = await booking_repository.lock_seats_for_update(
        show_id=payload.show_id,
        seat_ids=payload.seat_ids,
    )
    if len(locked_seats) != len(payload.seat_ids):
        raise BadRequestException("One or more seats are unavailable")

    existing_tickets = await booking_repository.get_existing_tickets(
        show_id=payload.show_id,
        seat_ids=payload.seat_ids,
    )
    if existing_tickets:
        raise BadRequestException("One or more seats are already booked")

    total_price = Decimal("0.00")
    for seat in locked_seats:
        total_price += Decimal(show.base_price) * Decimal(seat.price_multiplier)

    promocode = None
    if payload.promocode_id is not None:
        promocode = await booking_repository.get_promocode(payload.promocode_id)
        if not promocode or not promocode.is_active:
            raise BadRequestException("Invalid promocode")

    if promocode and promocode.discount_percent:
        total_price -= (
            total_price * Decimal(promocode.discount_percent) / Decimal("100")
        )

    total_price = total_price.quantize(Decimal("0.01"))

    order = Order(
        user_id=current_user.id,
        promocode_id=payload.promocode_id,
        idempotency_key=uuid4(),
        total_price=total_price,
        status=OrderStatusEnum.PENDING,
    )
    session.add(order)
    await session.flush()

    ticket_objects = []
    for seat in locked_seats:
        ticket_objects.append(
            Ticket(
                order_id=order.id,
                show_id=payload.show_id,
                seat_id=seat.id,
                price=Decimal(show.base_price) * Decimal(seat.price_multiplier),
            )
        )

    session.add_all(ticket_objects)
    await session.flush()
    checkout_url = await create_checkout_session(
        order=order, movie_title=f"Show #{show.id}"
    )
    return OrderResponse(
        id=order.id,
        user_id=order.user_id,
        promocode_id=order.promocode_id,
        idempotency_key=order.idempotency_key,
        total_price=order.total_price,
        status=order.status,
        created_at=order.created_at,
        ticket_ids=[ticket.id for ticket in ticket_objects],
        checkout_url=checkout_url,
    )


@booking_router.get("/orders/me", response_model=list[MyOrderDetailedResponse])
async def get_my_orders(
    current_user: User = Depends(get_current_user),
):
    query = (
        select(Order)
        .where(Order.user_id == current_user.id)
        .options(
            selectinload(Order.tickets)
            .selectinload(Ticket.seat)
            .selectinload(Seat.hall),
            selectinload(Order.tickets)
            .selectinload(Ticket.show)
            .selectinload(Show.movie),
            selectinload(Order.tickets)
            .selectinload(Ticket.show)
            .selectinload(Show.hall),
        )
        .order_by(Order.created_at.desc())
    )
    result = await session.execute(query)
    orders_db = result.scalars().all()

    response = []
    for order in orders_db:
        tickets_detail = []
        for ticket in order.tickets:
            tickets_detail.append(
                TicketDetailResponse(
                    ticket_id=ticket.id,
                    movie_title=ticket.show.movie.title,
                    hall_name=ticket.show.hall.name,
                    start_time=ticket.show.start_time,
                    row=ticket.seat.row_number,
                    seat=ticket.seat.seat_number,
                    price=ticket.price,
                    qr_code=ticket.qr_code_hash,
                )
            )

        response.append(
            MyOrderDetailedResponse(
                id=order.id,
                total_price=order.total_price,
                created_at=order.created_at,
                status=order.status.value,
                tickets=tickets_detail,
            )
        )
    return response
