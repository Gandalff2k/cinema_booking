from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import select, update

from app.models import Order, OrderStatusEnum, Ticket
from worker.tasks.cache_tasks import _release_stale_orders


async def _make_order(db, show, seat, *, status, age_minutes=0) -> Order:
    order = Order(
        user_id=None,
        idempotency_key=uuid4(),
        total_price=150,
        status=status,
    )
    db.add(order)
    await db.flush()
    db.add(Ticket(order_id=order.id, show_id=show.id, seat_id=seat.id, price=150))
    await db.commit()

    if age_minutes:
        # created_at has a server_default of now(); backdate it directly.
        await db.execute(
            update(Order)
            .where(Order.id == order.id)
            .values(created_at=datetime.now(UTC) - timedelta(minutes=age_minutes))
        )
        await db.commit()
    await db.refresh(order)
    return order


async def test_stale_pending_order_is_cancelled_and_seat_freed(db, make_show):
    show, seats = await make_show()
    order = await _make_order(
        db, show, seats[0], status=OrderStatusEnum.PENDING, age_minutes=50
    )

    await _release_stale_orders(minutes=40)

    await db.refresh(order)
    assert order.status == OrderStatusEnum.CANCELLED
    result = await db.execute(select(Ticket).where(Ticket.order_id == order.id))
    assert result.scalars().all() == []


async def test_recent_pending_order_is_left_alone(db, make_show):
    show, seats = await make_show()
    order = await _make_order(
        db, show, seats[0], status=OrderStatusEnum.PENDING, age_minutes=5
    )

    await _release_stale_orders(minutes=40)

    await db.refresh(order)
    assert order.status == OrderStatusEnum.PENDING
    result = await db.execute(select(Ticket).where(Ticket.order_id == order.id))
    assert len(result.scalars().all()) == 1


async def test_old_paid_order_is_never_touched(db, make_show):
    show, seats = await make_show()
    order = await _make_order(
        db, show, seats[0], status=OrderStatusEnum.PAID, age_minutes=999
    )

    await _release_stale_orders(minutes=40)

    await db.refresh(order)
    assert order.status == OrderStatusEnum.PAID
    result = await db.execute(select(Ticket).where(Ticket.order_id == order.id))
    assert len(result.scalars().all()) == 1
