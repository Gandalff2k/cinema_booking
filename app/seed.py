import asyncio
import random
import uuid
from datetime import datetime, timedelta
from decimal import Decimal

from faker import Faker
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.models.domain import (
    Cinema,
    FormatEnum,
    Genre,
    Hall,
    Movie,
    Review,
    RoleEnum,
    Seat,
    SeatTypeEnum,
    Show,
    User,
)
from core.config import config as app_config
from core.security.password import get_password_hash

fake = Faker(["uk_UA"])


async def clear_database(session):
    print("Database cleanup: truncating all tables...")

    await session.execute(
        text("""
        TRUNCATE users, movies, genres, cinemas, halls, seats, shows, 
        promocodes, orders, transactions, tickets, reviews RESTART IDENTITY CASCADE;
    """)
    )
    await session.commit()
    print("Database is clean!\n")


async def seed_data():
    engine = create_async_engine(app_config.POSTGRES_URL, echo=False)
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    async with async_session() as session:
        await clear_database(session)

        genres = [
            "Fantasy",
            "Action",
            "Drama",
            "Comedy",
            "Animation",
            "Thriller",
            "Horror",
            "Series",
        ]
        genres_objs = [Genre(name=name) for name in genres]
        session.add_all(genres_objs)
        await session.flush()

        cinema_lviv = Cinema(
            name="CinemaX Forum", city="Lviv", address="str. Chornovola, 2"
        )
        cinema_kyiv = Cinema(
            name="CinemaX Gulliver", city="Kyiv", address="str. Sport Plaza, 1"
        )
        session.add_all([cinema_lviv, cinema_kyiv])
        await session.flush()

        halls = [
            Hall(cinema_id=cinema_lviv.id, name="Hall 1 (IMAX)", capacity=30),
            Hall(cinema_id=cinema_lviv.id, name="Hall 2 (VIP)", capacity=18),
            Hall(cinema_id=cinema_kyiv.id, name="Main Hall", capacity=30),
            Hall(cinema_id=cinema_kyiv.id, name="Indie Hall", capacity=24),
        ]
        session.add_all(halls)
        await session.flush()

        def create_seats_for_hall(hall_id, rows, seats_per_row, has_vip=True):
            for r in range(1, rows + 1):
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

        create_seats_for_hall(halls[0].id, 4, 8)  # Lviv IMAX
        create_seats_for_hall(
            halls[1].id, 3, 6, has_vip=True
        )  # Lviv VIP (all sofas will be at the end)
        create_seats_for_hall(halls[2].id, 4, 8)  # Kyiv Main
        create_seats_for_hall(halls[3].id, 3, 8, has_vip=False)  # Kyiv Indie (no VIP)
        await session.flush()

        movie_data = [
            ("Aurum", "aurum.jpg", 110, "16+", 6),
            ("The Backrooms", "backrooms.jpg", 105, "18+", 6),
            ("Deadpool and Wolverine", "deadpool.webp", 127, "18+", 1),
            ("The Devil Wears Prada 2", "devilwearsprada2.jpg", 115, "12+", 3),
            ("Dune: Part Two", "dune2.webp", 166, "12+", 0),
            ("The Mandalorian and Grogu", "mandalorian.jpg", 140, "12+", 0),
            (
                "Oppenheimer",
                "oppenheirmer.webp",
                180,
                "16+",
                2,
            ),
            ("Pressure", "pressure.jpg", 95, "16+", 5),
            ("The Boys: Season 4", "theboys.jpg", 130, "18+", 7),
            ("Very Scary Movie 6", "veryscaryfilm.jpg", 90, "18+", 3),
        ]

        movie_objs = []
        for title, filename, dur, rating, genre_idx in movie_data:
            movie = Movie(
                title=title,
                description=fake.paragraph(nb_sentences=3),
                poster_url=f"/media/movies/{filename}",  #
                duration_minutes=dur,
                age_rating=rating,
                release_date=fake.date_between(start_date="-1y", end_date="today"),
            )
            movie.genres.append(genres_objs[genre_idx])
            session.add(movie)
            movie_objs.append(movie)

        extra_movies = [
            ("Night Flight", "nichniy_polit.jpg"),
            ("The Last Ridge", "ostanniy_rubizh.jpg"),
            ("Shadows of the City", "tini_mista.webp"),
            ("Stellar Dust", "zoryaniy_pyl.jpg"),
            ("Icy Heart", "kryzhane_sertse.jpg"),
            ("Flame of Vengeance", "polumya_pomsty.webp"),
            ("The Code of Silence", "kod_movchannya.jpg"),
            ("The Lost Hour", "vtracheniy_chas.jpg"),
            ("The Steel Storm", "staleviy_shtorm.jpg"),
            ("The Game of Fate", "gra_doli.jpg"),
            ("The Border of Reality", "mezha_realnosti.jpg"),
            ("The Awakening", "probudzhennya.jpg"),
            ("The Dark Forest", "temniy_lis.jpg"),
            ("The Golden Cage", "zolota_klitka.jpg"),
            ("The Exit 8", "vyhid_8.jpg"),
            ("The Resonance", "rezonans.jpg"),
            ("The Territory of X", "terytoriya_x.jpg"),
            ("The Escape from Shawshank", "vtecha_z_shoushenka.webp"),
            ("Men in Black 2", "lydi_v_chornomy_2.jpg"),
            (
                "Men in Black: Days of the Past",
                "lydi_iks_dni_munylogo_maybytnogo.jpg",
            ),
        ]
        age_ratings = ["12+", "16+", "18+"]
        for title, filename in extra_movies:
            movie = Movie(
                title=title,
                description=fake.paragraph(nb_sentences=3),
                poster_url=f"/media/movies/{filename}",
                duration_minutes=random.randint(85, 175),
                age_rating=random.choice(age_ratings),
                release_date=fake.date_between(start_date="-1y", end_date="today"),
            )
            movie.genres.append(random.choice(genres_objs))
            session.add(movie)
            movie_objs.append(movie)
        await session.flush()

        print("seed shows")
        shows_objs = []
        base_date = datetime.now().replace(hour=10, minute=0, second=0, microsecond=0)

        schedule_pool = random.sample(movie_objs, len(movie_objs))
        pool_idx = 0

        for day in range(3):
            for hall in halls:
                current_time = base_date + timedelta(days=day)
                for _ in range(8):
                    movie = schedule_pool[pool_idx % len(schedule_pool)]
                    pool_idx += 1
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
                    current_time += timedelta(minutes=movie.duration_minutes + 30)
        await session.flush()

        print("seed users and reviews")
        for i in range(2000):
            user = User(
                uuid=uuid.uuid4(),
                email=f"user{i}_{fake.unique.email()}",
                phone_number=f"+380{random.randint(100000000, 999999999)}",
                password="hashed_password",
                username=f"user{i}_{fake.unique.user_name()}",
            )
            session.add(user)
            await session.flush()

            if random.random() < 0.3:
                review = Review(
                    user_id=user.id,
                    movie_id=random.choice(movie_objs).id,
                    rating=random.randint(5, 10),
                    comment=fake.text(max_nb_chars=150),
                )
                session.add(review)

        print(f"Creating admin user: {app_config.ADMIN_EMAIL}")
        admin = User(
            uuid=uuid.uuid4(),
            email=app_config.ADMIN_EMAIL,
            phone_number=f"+380{random.randint(100000000, 999999999)}",
            password=get_password_hash(app_config.ADMIN_PASSWORD),
            username=app_config.ADMIN_USERNAME,
            role=RoleEnum.ADMIN,
        )
        session.add(admin)

        await session.commit()
        print(
            f" Admin user created: {app_config.ADMIN_EMAIL} / {app_config.ADMIN_PASSWORD}"
        )


if __name__ == "__main__":
    asyncio.run(seed_data())
