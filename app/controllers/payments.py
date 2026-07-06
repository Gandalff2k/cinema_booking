import stripe
from uuid import UUID
from fastapi import APIRouter, Request, Header
from sqlalchemy import select, delete

from core.config import config
from core.database import session
from core.exceptions import BadRequestException
from app.models import (
    Order,
    OrderStatusEnum,
    Ticket,
    Transaction,
    TransactionStatusEnum,
)

from worker.tasks.tickets import send_ticket_task

payments_router = APIRouter(tags=["Payments"])


@payments_router.post("/webhook/stripe")
async def stripe_webhook(request: Request, stripe_signature: str = Header(None)):
    """
    Слухає вебхуки від Stripe. Перевіряє підпис, фіксує оплату і відправляє квитки.
    """
    if not config.STRIPE_WEBHOOK_SECRET:
        raise BadRequestException("Stripe webhook secret is not configured")

    payload = await request.body()

    try:
        event = stripe.Webhook.construct_event(
            payload, stripe_signature, config.STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        raise BadRequestException("Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise BadRequestException("Invalid signature")

    if event["type"] == "checkout.session.completed":
        checkout_session = event["data"]["object"]

        client_reference_id = getattr(checkout_session, "client_reference_id", None)
        if not client_reference_id:
            return {"status": "ignored", "reason": "No client_reference_id"}

        try:
            order_uuid = UUID(client_reference_id)
        except ValueError:
            raise BadRequestException("Invalid Order UUID format")

        stripe_payment_intent = getattr(checkout_session, "payment_intent", None)
        amount_total = getattr(checkout_session, "amount_total", 0)

        try:
            order_result = await session.execute(
                select(Order)
                .where(Order.idempotency_key == order_uuid)
                .with_for_update()
            )
            order = order_result.scalar_one_or_none()

            if order is None:
                raise BadRequestException("Order not found")

            existing_transaction = await session.scalar(
                select(Transaction).where(
                    Transaction.liqpay_order_id == stripe_payment_intent
                )
            )
            if existing_transaction is not None:
                return {"status": "ok", "message": "Already processed"}

            actual_amount = amount_total / 100.0

            order.status = OrderStatusEnum.PAID

            session.add(
                Transaction(
                    order_id=order.id,
                    liqpay_order_id=stripe_payment_intent,
                    amount=actual_amount,
                    status=TransactionStatusEnum.SUCCESS,
                )
            )

            await session.commit()

        except Exception as db_exception:
            await session.rollback()
            raise db_exception

        send_ticket_task.delay(order.id)

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

                await session.commit()  # Фіксуємо відміну
            except Exception as db_exception:
                await session.rollback()
                raise db_exception

    return {"status": "success"}


#     from __future__ import annotations

# import json
# from decimal import Decimal, InvalidOperation
# from uuid import UUID
# from urllib.parse import parse_qs

# from fastapi import APIRouter, Request
# from sqlalchemy import delete, select

# from app.integrations.liqpay import verify_callback
# from app.models import Order, OrderStatusEnum, Ticket, Transaction, TransactionStatusEnum
# from core.database import Propagation, Transactional, session
# from core.exceptions import BadRequestException

# payments_router = APIRouter(tags=["Payments"])


# def _extract_callback_payload(raw_body: bytes, content_type: str) -> tuple[str, str]:
#     if not raw_body:
#         raise BadRequestException("Empty LiqPay callback payload")

#     if "application/json" in content_type:
#         try:
#             body = json.loads(raw_body.decode("utf-8"))
#         except (UnicodeDecodeError, json.JSONDecodeError) as exc:
#             raise BadRequestException("Invalid LiqPay callback payload") from exc

#         data = body.get("data")
#         signature = body.get("signature")
#     else:
#         try:
#             parsed = parse_qs(raw_body.decode("utf-8"), keep_blank_values=True)
#         except UnicodeDecodeError as exc:
#             raise BadRequestException("Invalid LiqPay callback payload") from exc

#         data = (parsed.get("data") or [None])[0]
#         signature = (parsed.get("signature") or [None])[0]

#     if not data or not signature:
#         raise BadRequestException("LiqPay callback requires data and signature")

#     return data, signature


# @payments_router.post("/callback")
# @Transactional(propagation=Propagation.REQUIRED)
# async def liqpay_callback(request: Request) -> dict[str, str]:
#     data, signature = _extract_callback_payload(
#         raw_body=await request.body(),
#         content_type=request.headers.get("content-type", ""),
#     )
#     payload = verify_callback(data=data, signature=signature)

#     order_id = payload.get("order_id")
#     if not order_id:
#         raise BadRequestException("LiqPay callback missing order_id")

#     try:
#         order_uuid = UUID(str(order_id))
#     except ValueError as exc:
#         raise BadRequestException("Invalid LiqPay order_id") from exc

#     order_result = await session.execute(
#         select(Order).where(Order.idempotency_key == order_uuid).with_for_update()
#     )
#     order = order_result.scalar_one_or_none()
#     if order is None:
#         raise BadRequestException("Order not found")

#     existing_transaction = await session.scalar(
#         select(Transaction).where(Transaction.liqpay_order_id == str(order_uuid))
#     )
#     if existing_transaction is not None:
#         return {"status": "ok"}

#     status = str(payload.get("status", "")).lower()
#     if status not in {"success", "failure"}:
#         return {"status": "ok"}

#     callback_amount = payload.get("amount")
#     if callback_amount is None:
#         raise BadRequestException("LiqPay callback missing amount")

#     try:
#         callback_amount_decimal = Decimal(str(callback_amount)).quantize(Decimal("0.01"))
#     except (InvalidOperation, ValueError) as exc:
#         raise BadRequestException("Invalid LiqPay callback amount") from exc

#     order_amount = Decimal(str(order.total_price)).quantize(Decimal("0.01"))
#     if callback_amount_decimal != order_amount:
#         raise BadRequestException("LiqPay amount does not match the order total")

#     if status == "success":
#         order.status = OrderStatusEnum.PAID
#         session.add(
#             Transaction(
#                 order_id=order.id,
#                 liqpay_order_id=str(order.idempotency_key),
#                 amount=order.total_price,
#                 status=TransactionStatusEnum.SUCCESS,
#             )
#         )
#     else:
#         order.status = OrderStatusEnum.CANCELLED
#         await session.execute(delete(Ticket).where(Ticket.order_id == order.id))
#         session.add(
#             Transaction(
#                 order_id=order.id,
#                 liqpay_order_id=str(order.idempotency_key),
#                 amount=order.total_price,
#                 status=TransactionStatusEnum.FAILURE,
#             )
#         )

#     await session.flush()
#     return {"status": "ok"}
