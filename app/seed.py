import asyncio
import random
import uuid
from decimal import Decimal
from datetime import datetime, timedelta, date
from faker import Faker
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from core.config import config as app_config
from app.models.domain import (
    User,
    Movie,
    Genre,
    Cinema,
    Hall,
    Seat,
    Show,
    Review,
    RoleEnum,
    SeatTypeEnum,
    FormatEnum,
    ShowStatusEnum,
)

fake = Faker(["uk_UA"])


async def clear_database(session):
    print(" Очищення старої бази даних...")
    # CASCADE видалить всі зв'язані дані, а RESTART IDENTITY скине ID (1, 2, 3...)
    await session.execute(
        text("""
        TRUNCATE users, movies, genres, cinemas, halls, seats, shows, 
        promocodes, orders, transactions, tickets, reviews RESTART IDENTITY CASCADE;
    """)
    )
    await session.commit()
    print(" База кристально чиста!\n")


async def seed_data():
    engine = create_async_engine(app_config.POSTGRES_URL, echo=False)
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    async with async_session() as session:
        # 1. ПОВНЕ ОЧИЩЕННЯ
        await clear_database(session)

        print(
            "docker compose exec minio mc alias set myminio http://localhost:9000 admin supersecretpasswordПочаток генерації нової мережі кінотеатрів..."
        )

        # 2. ЖАНРИ
        genres = [
            "Фантастика",
            "Бойовик",
            "Драма",
            "Комедія",
            "Мультфільм",
            "Триллер",
            "Жахи",
            "Серіал",
        ]
        genres_objs = [Genre(name=name) for name in genres]
        session.add_all(genres_objs)
        await session.flush()

        # 3. КІНОТЕАТРИ ТА ЗАЛИ (2 міста, 4 зали)
        cinema_lviv = Cinema(
            name="CinemaX Forum", city="Львів", address="вул. Під Дубом, 7B"
        )
        cinema_kyiv = Cinema(
            name="CinemaX Gulliver", city="Київ", address="Спортивна площа, 1A"
        )
        session.add_all([cinema_lviv, cinema_kyiv])
        await session.flush()

        halls = [
            Hall(cinema_id=cinema_lviv.id, name="Зал 1 (IMAX)", capacity=30),
            Hall(cinema_id=cinema_lviv.id, name="Зал 2 (VIP)", capacity=18),
            Hall(cinema_id=cinema_kyiv.id, name="Головний Зал", capacity=30),
            Hall(cinema_id=cinema_kyiv.id, name="Зал Інді", capacity=24),
        ]
        session.add_all(halls)
        await session.flush()

        # 4. ГЕНЕРАЦІЯ МІСЦЬ ДЛЯ ВСІХ ЗАЛІВ
        def create_seats_for_hall(hall_id, rows, seats_per_row, has_vip=True):
            for r in range(1, rows + 1):
                # Останній ряд робимо VIP диванчиками
                is_vip = has_vip and (r == rows)
                s_count = seats_per_row - 2 if is_vip else seats_per_row

                for s in range(1, s_count + 1):
                    session.add(
                        Seat(
                            hall_id=hall_id,
                            row_number=r,
                            seat_number=s,
                            seat_type=SeatTypeEnum.VIP
                            if is_vip
                            else SeatTypeEnum.STANDARD,
                            price_multiplier=Decimal("1.50")
                            if is_vip
                            else Decimal("1.00"),
                        )
                    )

        create_seats_for_hall(halls[0].id, 4, 8)  # Львів IMAX
        create_seats_for_hall(
            halls[1].id, 3, 6, has_vip=True
        )  # Львів VIP (усі дивани будуть в кінці)
        create_seats_for_hall(halls[2].id, 4, 8)  # Київ Головний
        create_seats_for_hall(halls[3].id, 3, 8, has_vip=False)  # Київ Інді (без VIP)
        await session.flush()

        # 5. ФІЛЬМИ (Твої 10 постерів з правильними розширеннями)
        movie_data = [
            ("Аурум", "aurum.jpg", 110, "16+", 6),
            ("Закулісся", "backrooms.jpg", 105, "18+", 6),
            ("Дедпул та Росомаха", "deadpool.webp", 127, "18+", 1),
            ("Диявол носить Prada 2", "devilwearsprada2.jpg", 115, "12+", 3),
            ("Дюна: Частина друга", "dune2.webp", 166, "12+", 0),
            ("Мандалорець та Грогу", "mandalorian.jpg", 140, "12+", 0),
            (
                "Оппенгеймер",
                "oppenheirmer.webp",
                180,
                "16+",
                2,
            ),  # Зберіг твою опечатку у файлі
            ("Тиск", "pressure.jpg", 95, "16+", 5),
            ("Хлопаки: Сезон 4", "theboys.jpg", 130, "18+", 7),
            ("Дуже страшне кіно 6", "veryscaryfilm.jpg", 90, "18+", 3),
        ]

        movie_objs = []
        for title, filename, dur, rating, genre_idx in movie_data:
            movie = Movie(
                title=title,
                description=fake.paragraph(nb_sentences=3),
                poster_url=f"/media/movies/{filename}",  # Прямий шлях для Nginx!
                duration_minutes=dur,
                age_rating=rating,
                release_date=fake.date_between(start_date="-1y", end_date="today"),
            )
            movie.genres.append(genres_objs[genre_idx])
            session.add(movie)
            movie_objs.append(movie)
        await session.flush()

        # 6. ГЕНЕРАЦІЯ СЕАНСІВ (Крутимо кіно 3 дні підряд у всіх залах)
        print("Створюємо розклад сеансів...")
        shows_objs = []
        base_date = datetime.now().replace(hour=10, minute=0, second=0, microsecond=0)

        for day in range(3):  # Сьогодні, завтра, післязавтра
            for hall in halls:
                current_time = base_date + timedelta(days=day)
                # У кожному залі показуємо 4 рандомні фільми на день
                for _ in range(4):
                    movie = random.choice(movie_objs)
                    is_imax = "IMAX" in hall.name
                    show = Show(
                        movie_id=movie.id,
                        hall_id=hall.id,
                        start_time=current_time,
                        end_time=current_time
                        + timedelta(minutes=movie.duration_minutes),
                        base_price=Decimal("200.00") if is_imax else Decimal("150.00"),
                        format=FormatEnum.FORMAT_IMAX
                        if is_imax
                        else FormatEnum.FORMAT_2D,
                    )
                    session.add(show)
                    shows_objs.append(show)
                    # Наступний сеанс через тривалість фільму + 30 хв на прибирання
                    current_time += timedelta(minutes=movie.duration_minutes + 30)
        await session.flush()

        # 7. МАСОВІ КОРИСТУВАЧІ ТА ВІДГУКИ
        print("Реєструємо 2000 користувачів та пишемо відгуки...")
        for i in range(2000):
            user = User(
                uuid=uuid.uuid4(),
                email=f"user{i}_{fake.unique.email()}",  # гарантована унікальність
                phone_number=f"+380{random.randint(100000000, 999999999)}",
                password="hashed_password",
                username=f"user{i}_{fake.unique.user_name()}",
            )
            session.add(user)
            await session.flush()  # Треба ID юзера для відгуку

            # 30% юзерів залишають відгук
            if random.random() < 0.3:
                review = Review(
                    user_id=user.id,
                    movie_id=random.choice(movie_objs).id,
                    rating=random.randint(
                        5, 10
                    ),  # Українці добрі, ставлять високі оцінки
                    comment=fake.text(max_nb_chars=150),
                )
                session.add(review)

        await session.commit()
        print(" БАЗА ЗАРЯДЖЕНА! Можна тестувати API.")


if __name__ == "__main__":
    asyncio.run(seed_data())
