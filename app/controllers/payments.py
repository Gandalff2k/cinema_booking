from uuid import UUID

import stripe
from fastapi import APIRouter, Header, Request
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError

from app.models import (
    Order,
    OrderStatusEnum,
    Ticket,
    Transaction,
    TransactionStatusEnum,
)
from core.config import config
from core.database import session
from core.exceptions import BadRequestException
from worker.tasks.cache_tasks import recalculate_popular_movies_task
from worker.tasks.tickets import send_ticket_task

payments_router = APIRouter(prefix="/payments", tags=["Payments"])


@payments_router.post("/webhook/stripe")
async def stripe_webhook(request: Request, stripe_signature: str = Header(None)):
    if not config.STRIPE_WEBHOOK_SECRET:
        raise BadRequestException("Stripe webhook secret is not configured")

    payload = await request.body()

    try:
        event = stripe.Webhook.construct_event(
            payload, stripe_signature, config.STRIPE_WEBHOOK_SECRET
        )
    except ValueError as exc:
        raise BadRequestException("Invalid payload") from exc
    except stripe.error.SignatureVerificationError as exc:
        raise BadRequestException("Invalid signature") from exc

    if event["type"] == "checkout.session.completed":
        checkout_session = event["data"]["object"]

        client_reference_id = getattr(checkout_session, "client_reference_id", None)
        if not client_reference_id:
            return {"status": "ignored", "reason": "No client_reference_id"}

        try:
            order_uuid = UUID(client_reference_id)
        except ValueError as exc:
            raise BadRequestException("Invalid Order UUID format") from exc

        stripe_payment_intent = getattr(checkout_session, "payment_intent", None)
        amount_total = getattr(checkout_session, "amount_total", 0)

        newly_paid = False
        order_id: int | None = None
        try:
            order = await session.scalar(
                select(Order)
                .where(Order.idempotency_key == order_uuid)
                .with_for_update()
            )
            if order is None:
                raise BadRequestException("Order not found")

            order_id = order.id

            # Guard against any non-PENDING state, not just PAID: if the stale-
            # order sweep already cancelled this order (and freed its seats) a
            # late webhook must never resurrect it into PAID with no tickets.
            if order.status != OrderStatusEnum.PENDING:
                await session.commit()
                return {
                    "status": "ok",
                    "message": f"Order not pending (status={order.status.value})",
                }

            order.status = OrderStatusEnum.PAID
            session.add(
                Transaction(
                    order_id=order.id,
                    provider_payment_id=stripe_payment_intent,
                    amount=amount_total / 100.0,
                    status=TransactionStatusEnum.SUCCESS,
                )
            )
            await session.commit()
            newly_paid = True
        except IntegrityError:
            await session.rollback()
            return {"status": "ok", "message": "Already processed"}
        except Exception as db_exception:
            await session.rollback()
            raise db_exception

        if newly_paid and order_id is not None:
            send_ticket_task.delay(order_id)
            recalculate_popular_movies_task.delay()

    elif event["type"] == "checkout.session.expired":
        checkout_session = event["data"]["object"]
        client_reference_id = getattr(checkout_session, "client_reference_id", None)

        if client_reference_id:
            try:
                order_result = await session.execute(
                    select(Order)
                    .where(Order.idempotency_key == UUID(client_reference_id))
                    .with_for_update()
                )
                order = order_result.scalar_one_or_none()
                if order and order.status == OrderStatusEnum.PENDING:
                    order.status = OrderStatusEnum.CANCELLED
                    await session.execute(
                        delete(Ticket).where(Ticket.order_id == order.id)
                    )

                await session.commit()
            except Exception as db_exception:
                await session.rollback()
                raise db_exception

    return {"status": "success"}
