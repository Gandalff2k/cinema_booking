import time

from fastapi import HTTPException, Request, status

from core.cache.redis_backend import redis
from core.config import config


class RateLimiter:
    def __init__(
        self,
        times: int | None = None,
        seconds: int | None = None,
        prefix: str = "ratelimit",
    ):
        self.times = times if times is not None else config.RATE_LIMIT_TIMES
        self.window = (
            seconds if seconds is not None else config.RATE_LIMIT_WINDOW_SECONDS
        )
        self.prefix = prefix

    @staticmethod
    def _client_ip(request: Request) -> str:
        # Honour the proxy (nginx) forwarded header, fall back to the socket peer.
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    async def __call__(self, request: Request) -> None:
        if not config.RATE_LIMIT_ENABLED:
            return

        window_id = int(time.time()) // self.window
        key = f"{self.prefix}:{request.url.path}:{self._client_ip(request)}:{window_id}"

        current = await redis.incr(key)
        if current == 1:
            # First hit in this window — set the expiry so the key self-cleans.
            await redis.expire(key, self.window)

        if current > self.times:
            ttl = await redis.ttl(key)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Please slow down.",
                headers={"Retry-After": str(ttl if ttl > 0 else self.window)},
            )
