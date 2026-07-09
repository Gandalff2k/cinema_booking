import time

import stripe

from app.models import Order
from core.config import config
from core.exceptions import BadRequestException

stripe.api_key = config.STRIPE_SECRET_KEY

# Stripe hard-enforces a 30-minute minimum and 24-hour maximum on checkout
# session expiry, regardless of what's requested.
_STRIPE_MIN_EXPIRY_SECONDS = 30 * 60
_STRIPE_MAX_EXPIRY_SECONDS = 24 * 60 * 60


async def create_checkout_session(order: Order, movie_title: str) -> str:
    if not config.STRIPE_SECRET_KEY:
        raise BadRequestException("Stripe credentials are not configured")

    amount_in_cents = int(order.total_price * 100)

    # Align Stripe's own session expiry to our stale-order window (clamped to
    # what Stripe allows) so `checkout.session.expired` fires the cancellation
    # through the existing, race-safe webhook path instead of leaving it to
    # the blunter periodic sweep alone.
    expires_in = max(
        _STRIPE_MIN_EXPIRY_SECONDS,
        min(config.STALE_ORDER_MINUTES * 60, _STRIPE_MAX_EXPIRY_SECONDS),
    )

    try:
        session = await stripe.checkout.Session.create_async(
            payment_method_types=["card"],
            line_items=[
                {
                    "price_data": {
                        "currency": "uah",
                        "product_data": {
                            "name": f"Tickets for: {movie_title}",
                            "description": f"Order #{order.id}",
                        },
                        "unit_amount": amount_in_cents,
                    },
                    "quantity": 1,
                }
            ],
            mode="payment",
            client_reference_id=str(order.idempotency_key),
            expires_at=int(time.time()) + expires_in,
            success_url=f"{config.FRONTEND_URL}/pages/profile/index.html",
            cancel_url=f"{config.FRONTEND_URL}/pages/home/index.html",
        )
        return session.url
    except stripe.error.StripeError as e:
        raise BadRequestException(f"Failed to create Stripe session: {str(e)}") from e
