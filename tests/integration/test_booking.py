from unittest.mock import AsyncMock, patch
from uuid import uuid4

from sqlalchemy import select

from app.models import Order, OrderStatusEnum, Ticket


async def test_get_seats_for_show(client, make_show):
    show, seats = await make_show(seat_count=4)
    r = await client.get(f"/v1/booking/shows/{show.id}/seats")
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 4
    assert all(not s["is_occupied"] for s in body)


async def test_create_order_requires_auth(client, make_show):
    show, seats = await make_show()
    r = await client.post(
        "/v1/booking/orders",
        json={"show_id": show.id, "seat_ids": [seats[0].id]},
    )
    assert r.status_code == 401


async def test_create_order_happy_path(client, user_headers, make_show):
    show, seats = await make_show(seat_count=4, base_price=150)
    with patch(
        "api.v1.booking.create_checkout_session",
        new=AsyncMock(return_value="https://checkout.stripe.com/fake-session"),
    ):
        r = await client.post(
            "/v1/booking/orders",
            json={"show_id": show.id, "seat_ids": [seats[0].id, seats[1].id]},
            headers=user_headers,
        )
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "pending"
    assert body["checkout_url"] == "https://checkout.stripe.com/fake-session"
    assert len(body["ticket_ids"]) == 2
    assert float(body["total_price"]) == 300.0  # 2 seats * 150, multiplier 1.0

    # The booked seats are now reported occupied.
    seats_after = (await client.get(f"/v1/booking/shows/{show.id}/seats")).json()
    occupied_ids = {s["id"] for s in seats_after if s["is_occupied"]}
    assert occupied_ids == {seats[0].id, seats[1].id}


async def test_create_order_duplicate_seat_ids_rejected(
    client, user_headers, make_show
):
    show, seats = await make_show()
    r = await client.post(
        "/v1/booking/orders",
        json={"show_id": show.id, "seat_ids": [seats[0].id, seats[0].id]},
        headers=user_headers,
    )
    assert r.status_code == 400


async def test_create_order_nonexistent_show_404(client, user_headers, make_show):
    _show, seats = await make_show()
    r = await client.post(
        "/v1/booking/orders",
        json={"show_id": 999999, "seat_ids": [seats[0].id]},
        headers=user_headers,
    )
    assert r.status_code == 404


async def test_create_order_already_booked_seat_rejected(
    client, user_headers, make_show, db
):
    show, seats = await make_show()
    # Simulate a ticket already sold for this seat on this show.
    order = Order(
        user_id=None,
        idempotency_key=uuid4(),
        total_price=150,
        status=OrderStatusEnum.PAID,
    )
    db.add(order)
    await db.flush()
    db.add(Ticket(order_id=order.id, show_id=show.id, seat_id=seats[0].id, price=150))
    await db.commit()

    r = await client.post(
        "/v1/booking/orders",
        json={"show_id": show.id, "seat_ids": [seats[0].id]},
        headers=user_headers,
    )
    assert r.status_code == 400


async def test_get_my_orders_requires_auth(client):
    assert (await client.get("/v1/booking/orders/me")).status_code == 401


async def test_get_my_orders_lists_own_orders(client, user_headers, make_show):
    show, seats = await make_show()
    with patch(
        "api.v1.booking.create_checkout_session",
        new=AsyncMock(return_value="https://checkout.stripe.com/fake-session"),
    ):
        await client.post(
            "/v1/booking/orders",
            json={"show_id": show.id, "seat_ids": [seats[0].id]},
            headers=user_headers,
        )
    r = await client.get("/v1/booking/orders/me", headers=user_headers)
    assert r.status_code == 200
    orders = r.json()
    assert len(orders) == 1
    assert orders[0]["status"] == "pending"
    assert len(orders[0]["tickets"]) == 1


async def test_seat_lock_prevents_double_booking(client, user_headers, make_show, db):
    """Two orders for the same seat: the second must fail once tickets exist,
    proving the seat lock + existing-ticket check actually stops overselling."""
    show, seats = await make_show()
    with patch(
        "api.v1.booking.create_checkout_session",
        new=AsyncMock(return_value="https://checkout.stripe.com/fake-session"),
    ):
        first = await client.post(
            "/v1/booking/orders",
            json={"show_id": show.id, "seat_ids": [seats[0].id]},
            headers=user_headers,
        )
        assert first.status_code == 201

        second = await client.post(
            "/v1/booking/orders",
            json={"show_id": show.id, "seat_ids": [seats[0].id]},
            headers=user_headers,
        )
    assert second.status_code == 400

    result = await db.execute(select(Ticket).where(Ticket.seat_id == seats[0].id))
    assert len(result.scalars().all()) == 1
