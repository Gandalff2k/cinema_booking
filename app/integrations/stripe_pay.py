import stripe
from app.models import Order
from core.config import config
from core.exceptions import BadRequestException

stripe.api_key = config.STRIPE_SECRET_KEY


async def create_checkout_session(order: Order, movie_title: str) -> str:
    """
    Створює сесію оплати у Stripe і повертає URL для редиректу користувача.
    """
    if not config.STRIPE_SECRET_KEY:
        raise BadRequestException("Stripe credentials are not configured")

    amount_in_cents = int(order.total_price * 100)

    try:
        session = await stripe.checkout.Session.create_async(
            payment_method_types=["card"],
            line_items=[
                {
                    "price_data": {
                        "currency": "uah",
                        "product_data": {
                            "name": f"Квитки на сеанс: {movie_title}",
                            "description": f"Замовлення #{order.id}",
                        },
                        "unit_amount": amount_in_cents,
                    },
                    "quantity": 1,
                }
            ],
            mode="payment",
            client_reference_id=str(order.idempotency_key),
            success_url=f"{config.FRONTEND_URL}/pages/profile/index.html",
            cancel_url=f"{config.FRONTEND_URL}/pages/home/index.html",
        )
        return session.url
    except Exception as e:
        raise BadRequestException(f"Failed to create Stripe session: {str(e)}")
