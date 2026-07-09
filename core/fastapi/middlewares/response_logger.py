import json
import logging
import time

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from core.config import config

logger = logging.getLogger("app.request")

_LOG_BODIES = config.DEBUG and config.LOG_REQUEST_BODY
_MAX_BODY_CHARS = 2000
_BODY_METHODS = {"POST", "PUT", "PATCH"}


def _redact_body(raw: bytes) -> str:
    text = raw.decode("utf-8", errors="replace")
    try:
        data = json.loads(text)
    except (ValueError, TypeError):
        data = None

    if isinstance(data, dict):
        for key in list(data):
            if any(s in key.lower() for s in ("password", "token", "secret")):
                data[key] = "***"
        text = json.dumps(data, ensure_ascii=False)

    if len(text) > _MAX_BODY_CHARS:
        text = f"{text[:_MAX_BODY_CHARS]}...(truncated)"
    return text


class ResponseLoggerMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        if _LOG_BODIES and scope.get("method") in _BODY_METHODS:
            receive = await self._log_request_body(scope, receive)

        start = time.perf_counter()
        status_code = 500

        async def _send(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, _send)
        finally:
            duration_ms = (time.perf_counter() - start) * 1000
            if status_code >= 500:
                level = logging.ERROR
            elif status_code >= 400:
                level = logging.WARNING
            else:
                level = logging.INFO
            logger.log(
                level,
                "%s %s -> %s (%.1f ms)",
                scope.get("method"),
                scope.get("path"),
                status_code,
                duration_ms,
            )

    @staticmethod
    async def _log_request_body(scope: Scope, receive: Receive) -> Receive:
        """Drain the ASGI body, log it, then hand back a replaying receive()."""
        messages: list[Message] = []
        body = b""
        more_body = True
        while more_body:
            message = await receive()
            messages.append(message)
            if message["type"] == "http.request":
                body += message.get("body", b"")
                more_body = message.get("more_body", False)
            else:
                more_body = False

        if body:
            logger.debug(
                "Body %s %s: %s",
                scope.get("method"),
                scope.get("path"),
                _redact_body(body),
            )

        async def replay() -> Message:
            if messages:
                return messages.pop(0)
            return await receive()

        return replay
