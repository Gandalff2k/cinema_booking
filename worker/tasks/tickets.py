import asyncio
import hashlib
import hmac
import html
import io
import logging

import qrcode
from sqlalchemy import select
from sqlalchemy.orm import joinedload, selectinload

from app.integrations.email_sender import EmailAttachment, send_email
from app.models import Order, Seat, Show, Ticket
from core.config import config
from core.database import session, standalone_session
from worker import celery_app

logger = logging.getLogger(__name__)


def _make_ticket_token(ticket: Ticket, order: Order) -> str:
    """Deterministic signed token for a ticket (used as the QR payload)."""
    raw = f"{ticket.id}:{order.idempotency_key}".encode()
    return hmac.new(config.SECRET_KEY.encode("utf-8"), raw, hashlib.sha256).hexdigest()


def _render_qr_png(payload: str) -> bytes:
    image = qrcode.make(payload)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _build_email_html(order: Order) -> str:
    cards = []
    for ticket in order.tickets:
        show = ticket.show
        seat = ticket.seat
        cards.append(
            f"""
            <table width="100%" cellpadding="0" cellspacing="0"
                   style="background:#1e293b;border-radius:12px;margin-bottom:16px;">
              <tr>
                <td style="padding:18px;vertical-align:top;">
                  <div style="font-size:18px;font-weight:bold;color:#f8fafc;">
                    {html.escape(show.movie.title)}
                  </div>
                  <div style="color:#94a3b8;margin-top:6px;">
                    {html.escape(show.hall.name)} · {show.start_time:%d.%m.%Y %H:%M}
                  </div>
                  <div style="color:#94a3b8;">
                    Row {seat.row_number}, seat {seat.seat_number}
                  </div>
                  <div style="color:#38bdf8;font-weight:bold;margin-top:8px;">
                    {ticket.price} UAH
                  </div>
                </td>
                <td width="140" style="padding:18px;text-align:right;">
                  <img src="cid:qr{ticket.id}" width="120" height="120" alt="QR"
                       style="background:#fff;padding:6px;border-radius:8px;display:block;" />
                </td>
              </tr>
            </table>
            """
        )

    return f"""
    <div style="max-width:600px;margin:0 auto;font-family:Arial,Helvetica,sans-serif;
                background:#0f172a;border-radius:16px;overflow:hidden;">
      <div style="background:linear-gradient(90deg,#38bdf8,#818cf8);padding:26px;text-align:center;">
        <h1 style="margin:0;color:#0f172a;font-size:26px;">🍿 CinemaX</h1>
      </div>
      <div style="padding:26px;">
        <h2 style="color:#f8fafc;margin-top:0;">Thank you for your order #{order.id}!</h2>
        <p style="color:#94a3b8;">
          Payment received. Show each ticket's QR code at the entrance.
        </p>
        {"".join(cards)}
        <p style="color:#f8fafc;font-size:18px;font-weight:bold;text-align:right;">
          Total: {order.total_price} UAH
        </p>
      </div>
      <div style="background:#1e293b;padding:16px;text-align:center;color:#64748b;font-size:12px;">
        CinemaX · Automated message — please do not reply.
      </div>
    </div>
    """


@standalone_session
async def _process_ticket(order_id: int) -> None:
    query = (
        select(Order)
        .options(
            joinedload(Order.user),
            selectinload(Order.tickets).joinedload(Ticket.seat).joinedload(Seat.hall),
            selectinload(Order.tickets).joinedload(Ticket.show).joinedload(Show.movie),
            selectinload(Order.tickets).joinedload(Ticket.show).joinedload(Show.hall),
        )
        .where(Order.id == order_id)
    )
    result = await session.execute(query)
    order = result.scalar_one_or_none()

    if order is None or not order.tickets:
        logger.warning("Order %s has no tickets to process", order_id)
        return

    attachments: list[EmailAttachment] = []
    for ticket in order.tickets:
        token = _make_ticket_token(ticket, order)
        ticket.qr_code_hash = token
        attachments.append(
            EmailAttachment(
                filename=f"ticket_{ticket.id}.png",
                content=_render_qr_png(token),
                maintype="image",
                subtype="png",
                cid=f"qr{ticket.id}",
            )
        )

    await session.commit()

    if not order.user or not order.user.email:
        logger.warning(
            "Order %s has no user email; QR generated but not sent", order_id
        )
        return

    await send_email(
        to=order.user.email,
        subject=f"Your CinemaX tickets — order #{order.id}",
        html_body=_build_email_html(order),
        attachments=attachments,
    )
    logger.info("Tickets for order %s generated and emailed", order_id)


@celery_app.task(
    name="worker.tasks.tickets.send_ticket_task",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    max_retries=3,
)
def send_ticket_task(self, order_id: int) -> None:
    # Safe to retry: the QR token is a deterministic HMAC of (ticket, order),
    # so re-running just recomputes the same value and re-sends the same
    # email — a customer who paid never silently ends up with no ticket email
    # because of one transient SMTP/DB blip.
    asyncio.run(_process_ticket(order_id))
