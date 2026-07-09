import asyncio
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import asyncpg
import pytest
import pytest_asyncio
import redis.asyncio as aioredis
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.engine.url import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker

import app.models.domain  # noqa: F401  (register models on Base.metadata)
from app.models import (
    Cinema,
    FormatEnum,
    Hall,
    Movie,
    RoleEnum,
    Seat,
    SeatTypeEnum,
    Show,
    User,
)
from core.config import config
from core.database.session import Base, engines
from core.security.password import get_password_hash

TestSession = async_sessionmaker(engines["writer"], expire_on_commit=False)


@pytest.fixture(scope="session")
def event_loop():
    """Session-scoped loop so the session-scoped DB setup can be async."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


async def _ensure_database() -> None:
    url = make_url(config.DATABASE_URL)
    admin_conn = await asyncpg.connect(
        host=url.host,
        port=url.port,
        user=url.username,
        password=url.password,
        database="postgres",
    )
    try:
        exists = await admin_conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1", url.database
        )
        if not exists:
            await admin_conn.execute(f'CREATE DATABASE "{url.database}"')
    finally:
        await admin_conn.close()


@pytest_asyncio.fixture(scope="session")
async def _setup_db():
    await _ensure_database()
    async with engines["writer"].begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engines["writer"].begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(autouse=True)
async def _clean(_setup_db):
    tables = ", ".join(t.name for t in reversed(Base.metadata.sorted_tables))
    async with engines["writer"].begin() as conn:
        await conn.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))
    redis = aioredis.from_url(config.REDIS_URL)
    try:
        await redis.flushdb()
    finally:
        await redis.aclose()
    yield


@pytest_asyncio.fixture
async def client():
    from core.server import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest_asyncio.fixture
async def db():
    async with TestSession() as session:
        yield session


@pytest_asyncio.fixture
async def make_movie(db):
    async def _make(title="Test Movie", duration=120, active=True):
        movie = Movie(
            title=title,
            duration_minutes=duration,
            is_active=active,
            poster_url="/media/movies/test.jpg",
        )
        db.add(movie)
        await db.commit()
        await db.refresh(movie)
        return movie

    return _make


@pytest_asyncio.fixture
async def make_show(db, make_movie):

    async def _make(movie=None, seat_count=4, base_price=Decimal("150.00")):
        if movie is None:
            movie = await make_movie()

        cinema = Cinema(name="Test Cinema", city="Test City", address="Test St. 1")
        db.add(cinema)
        await db.flush()

        hall = Hall(cinema_id=cinema.id, name="Test Hall", capacity=seat_count)
        db.add(hall)
        await db.flush()

        seats = [
            Seat(
                hall_id=hall.id,
                row_number=1,
                seat_number=i + 1,
                seat_type=SeatTypeEnum.STANDARD,
                price_multiplier=Decimal("1.00"),
            )
            for i in range(seat_count)
        ]
        db.add_all(seats)
        await db.flush()

        start_time = datetime.now(UTC) + timedelta(hours=2)
        show = Show(
            movie_id=movie.id,
            hall_id=hall.id,
            start_time=start_time,
            end_time=start_time + timedelta(minutes=movie.duration_minutes),
            base_price=base_price,
            format=FormatEnum.FORMAT_2D,
        )
        db.add(show)
        await db.commit()
        for seat in seats:
            await db.refresh(seat)
        await db.refresh(show)
        return show, seats

    return _make


@pytest_asyncio.fixture
async def make_admin(db):
    async def _make(email="root@cinemax.com", password="admin12345"):
        user = User(
            email=email,
            username="root_admin",
            password=get_password_hash(password),
            role=RoleEnum.ADMIN,
        )
        db.add(user)
        await db.commit()
        return {"email": email, "password": password}

    return _make


@pytest_asyncio.fixture
async def user_headers(client):
    """Register + log in a normal user; return auth headers."""
    creds = {
        "email": "user@example.com",
        "username": "regular",
        "password": "password123",
    }
    await client.post("/v1/auth/register", json=creds)
    resp = await client.post(
        "/v1/auth/login",
        json={"contact": creds["email"], "password": creds["password"]},
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def admin_headers(client, make_admin):
    creds = await make_admin()
    resp = await client.post(
        "/v1/auth/login",
        json={"contact": creds["email"], "password": creds["password"]},
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
