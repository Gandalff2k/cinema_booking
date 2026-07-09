from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from sqlalchemy import select

from app.models import (
    Order,
    OrderStatusEnum,
    Ticket,
    Transaction,
    TransactionStatusEnum,
)
from core.config import config


def _event(event_type: str, **checkout_session_fields) -> dict:
    return {
        "type": event_type,
        "data": {"object": SimpleNamespace(**checkout_session_fields)},
    }


async def _make_pending_order(db, show, seats) -> Order:
    order = Order(
        user_id=None,
        idempotency_key=uuid4(),
        total_price=150,
        status=OrderStatusEnum.PENDING,
    )
    db.add(order)
    await db.flush()
    db.add(Ticket(order_id=order.id, show_id=show.id, seat_id=seats[0].id, price=150))
    await db.commit()
    await db.refresh(order)
    return order


async def test_webhook_requires_configured_secret(client, monkeypatch):
    monkeypatch.setattr(config, "STRIPE_WEBHOOK_SECRET", None)
    r = await client.post("/v1/payments/webhook/stripe", content=b"{}")
    assert r.status_code == 400


async def test_webhook_rejects_bad_signature(client, monkeypatch):
    monkeypatch.setattr(config, "STRIPE_WEBHOOK_SECRET", "whsec_test")
    r = await client.post(
        "/v1/payments/webhook/stripe",
        content=b"{}",
        headers={"stripe-signature": "not-a-real-signature"},
    )
    assert r.status_code == 400


async def test_checkout_completed_marks_order_paid(client, monkeypatch, db, make_show):
    monkeypatch.setattr(config, "STRIPE_WEBHOOK_SECRET", "whsec_test")
    show, seats = await make_show()
    order = await _make_pending_order(db, show, seats)

    event = _event(
        "checkout.session.completed",
        client_reference_id=str(order.idempotency_key),
        payment_intent="pi_test_123",
        amount_total=15000,
    )
    with patch("stripe.Webhook.construct_event", return_value=event):
        r = await client.post(
            "/v1/payments/webhook/stripe",
            content=b"{}",
            headers={"stripe-signature": "sig"},
        )
    assert r.status_code == 200

    await db.refresh(order)
    assert order.status == OrderStatusEnum.PAID
    txn = await db.scalar(select(Transaction).where(Transaction.order_id == order.id))
    assert txn is not None
    assert txn.status == TransactionStatusEnum.SUCCESS
    assert txn.provider_payment_id == "pi_test_123"


async def test_duplicate_webhook_delivery_is_idempotent(
    client, monkeypatch, db, make_show
):
    """Stripe redelivers events; the second delivery must not double-charge
    or create a second transaction."""
    monkeypatch.setattr(config, "STRIPE_WEBHOOK_SECRET", "whsec_test")
    show, seats = await make_show()
    order = await _make_pending_order(db, show, seats)

    event = _event(
        "checkout.session.completed",
        client_reference_id=str(order.idempotency_key),
        payment_intent="pi_test_dup",
        amount_total=15000,
    )
    with patch("stripe.Webhook.construct_event", return_value=event):
        first = await client.post(
            "/v1/payments/webhook/stripe",
            content=b"{}",
            headers={"stripe-signature": "sig"},
        )
        second = await client.post(
            "/v1/payments/webhook/stripe",
            content=b"{}",
            headers={"stripe-signature": "sig"},
        )
    assert first.status_code == 200
    assert second.status_code == 200
    assert "not pending" in second.json()["message"]

    result = await db.execute(
        select(Transaction).where(Transaction.order_id == order.id)
    )
    assert len(result.scalars().all()) == 1


async def test_late_webhook_cannot_resurrect_cancelled_order(
    client, monkeypatch, db, make_show
):
    """Regression: if the stale-order sweep already cancelled an order (and
    freed its seat), a late `checkout.session.completed` must NOT flip it back
    to PAID — that would leave a paid order with no tickets."""
    monkeypatch.setattr(config, "STRIPE_WEBHOOK_SECRET", "whsec_test")
    show, seats = await make_show()
    order = await _make_pending_order(db, show, seats)

    # Simulate the stale-order sweep having already run.
    order.status = OrderStatusEnum.CANCELLED
    await db.execute(Ticket.__table__.delete().where(Ticket.order_id == order.id))
    await db.commit()

    event = _event(
        "checkout.session.completed",
        client_reference_id=str(order.idempotency_key),
        payment_intent="pi_test_late",
        amount_total=15000,
    )
    with patch("stripe.Webhook.construct_event", return_value=event):
        r = await client.post(
            "/v1/payments/webhook/stripe",
            content=b"{}",
            headers={"stripe-signature": "sig"},
        )
    assert r.status_code == 200

    await db.refresh(order)
    assert order.status == OrderStatusEnum.CANCELLED  # never resurrected
    txn = await db.scalar(select(Transaction).where(Transaction.order_id == order.id))
    assert txn is None  # no phantom transaction for an order with no tickets


async def test_checkout_expired_cancels_pending_order_and_frees_seat(
    client, monkeypatch, db, make_show
):
    monkeypatch.setattr(config, "STRIPE_WEBHOOK_SECRET", "whsec_test")
    show, seats = await make_show()
    order = await _make_pending_order(db, show, seats)

    event = _event(
        "checkout.session.expired",
        client_reference_id=str(order.idempotency_key),
    )
    with patch("stripe.Webhook.construct_event", return_value=event):
        r = await client.post(
            "/v1/payments/webhook/stripe",
            content=b"{}",
            headers={"stripe-signature": "sig"},
        )
    assert r.status_code == 200

    await db.refresh(order)
    assert order.status == OrderStatusEnum.CANCELLED
    result = await db.execute(select(Ticket).where(Ticket.order_id == order.id))
    assert result.scalars().all() == []  # seat freed
