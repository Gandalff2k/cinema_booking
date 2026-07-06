# from __future__ import annotations

# import base64
# import hashlib
# import json
# from decimal import Decimal
# from typing import Any

# from app.models import Order
# from core.config import config
# from core.exceptions import BadRequestException


# def _get_public_key() -> str:
#     return config.LIQPAY_SANDBOX_PUBLIC_KEY or config.LIQPAY_PUBLIC_KEY


# def _get_private_key() -> str:
#     return config.LIQPAY_SANDBOX_PRIVATE_KEY or config.LIQPAY_PRIVATE_KEY


# def _build_signature(data: str, private_key: str) -> str:
#     signature_source = f"{private_key}{data}{private_key}".encode("utf-8")
#     digest = hashlib.sha1(signature_source).digest()
#     return base64.b64encode(digest).decode("utf-8")


# def generate_payment_data(order: Order) -> dict[str, str]:
#     public_key = _get_public_key()
#     private_key = _get_private_key()

#     if not public_key or not private_key:
#         raise BadRequestException("LiqPay credentials are not configured")

#     payload: dict[str, Any] = {
#         "public_key": public_key,
#         "version": "3",
#         "action": "pay",
#         "amount": str(Decimal(order.total_price).quantize(Decimal("0.01"))),
#         "currency": "UAH",
#         "description": f"Cinema order #{order.id}",
#         "order_id": str(order.idempotency_key),
#         "sandbox": 1,
#     }

#     data = base64.b64encode(
#         json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
#     ).decode("utf-8")

#     return {
#         "data": data,
#         "signature": _build_signature(data, private_key),
#     }


# def verify_callback(data: str, signature: str) -> dict[str, Any]:
#     private_key = _get_private_key()
#     if not private_key:
#         raise BadRequestException("LiqPay credentials are not configured")

#     expected_signature = _build_signature(data, private_key)
#     if not hashlib.compare_digest(expected_signature, signature):
#         raise BadRequestException("Invalid LiqPay signature")

#     try:
#         decoded_payload = base64.b64decode(data, validate=True).decode("utf-8")
#         payload = json.loads(decoded_payload)
#     except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
#         raise BadRequestException("Invalid LiqPay callback payload") from exc

#     if not isinstance(payload, dict):
#         raise BadRequestException("Invalid LiqPay callback payload")

#     return payload
