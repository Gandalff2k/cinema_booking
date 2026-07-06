import uuid
import enum
from sqlalchemy import (
    Column,
    Integer,
    BigInteger,
    String,
    Boolean,
    ForeignKey,
    Numeric,
    DateTime,
    Date,
    Text,
    Table,
    Index,
    UniqueConstraint,
    Enum,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from core.database import Base


class RoleEnum(str, enum.Enum):
    CLIENT = "client"
    MANAGER = "manager"
    ADMIN = "admin"


class SeatTypeEnum(str, enum.Enum):
    STANDARD = "standard"
    VIP = "vip"
    LOVE_SEAT = "love_seat"
    DISABLED = "disabled"


class FormatEnum(str, enum.Enum):
    FORMAT_2D = "2D"
    FORMAT_3D = "3D"
    FORMAT_IMAX = "IMAX"


class ShowStatusEnum(str, enum.Enum):
    SCHEDULED = "scheduled"
    ACTIVE = "active"
    FINISHED = "finished"
    CANCELLED = "cancelled"


class OrderStatusEnum(str, enum.Enum):
    PENDING = "pending"
    PAID = "paid"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class TransactionStatusEnum(str, enum.Enum):
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILURE = "failure"


movie_genres = Table(
    "movie_genres",
    Base.metadata,
    Column(
        "movie_id",
        BigInteger,
        ForeignKey("movies.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "genre_id",
        Integer,
        ForeignKey("genres.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class User(Base):
    __tablename__ = "users"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    phone_number = Column(String(20), unique=True, nullable=True)
    password = Column(String(255), nullable=False)
    username = Column(String(255), unique=True, nullable=False)

    role = Column(
        Enum(RoleEnum, name="role_enum"), default=RoleEnum.CLIENT, nullable=False
    )
    is_active = Column(Boolean, server_default="true", nullable=False)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    orders = relationship("Order", back_populates="user")
    reviews = relationship("Review", back_populates="user")

    __table_args__ = (Index("idx_users_email_phone", "email", "phone_number"),)


class Genre(Base):
    __tablename__ = "genres"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), unique=True, nullable=False)


class Movie(Base):
    __tablename__ = "movies"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    poster_url = Column(String(500), nullable=True)
    trailer_url = Column(String(500), nullable=True)
    duration_minutes = Column(Integer, nullable=False)
    age_rating = Column(String(10), nullable=True)
    release_date = Column(Date, nullable=True)
    is_active = Column(Boolean, server_default="true", nullable=False)

    genres = relationship("Genre", secondary=movie_genres, backref="movies")
    shows = relationship("Show", back_populates="movie")
    reviews = relationship("Review", back_populates="movie")


class Cinema(Base):
    __tablename__ = "cinemas"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(150), nullable=False)
    city = Column(String(100), nullable=False)
    address = Column(String(255), nullable=False)
    is_active = Column(Boolean, server_default="true", nullable=False)

    halls = relationship("Hall", back_populates="cinema")


class Hall(Base):
    __tablename__ = "halls"
    id = Column(Integer, primary_key=True, autoincrement=True)
    cinema_id = Column(
        Integer, ForeignKey("cinemas.id", ondelete="CASCADE"), nullable=False
    )
    name = Column(String(50), nullable=False)
    capacity = Column(Integer, nullable=False)

    cinema = relationship("Cinema", back_populates="halls")
    seats = relationship("Seat", back_populates="hall")
    shows = relationship("Show", back_populates="hall")


class Seat(Base):
    __tablename__ = "seats"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    hall_id = Column(
        Integer, ForeignKey("halls.id", ondelete="CASCADE"), nullable=False
    )
    row_number = Column(Integer, nullable=False)
    seat_number = Column(Integer, nullable=False)

    seat_type = Column(
        Enum(SeatTypeEnum, name="seat_type_enum"),
        default=SeatTypeEnum.STANDARD,
        nullable=False,
    )
    price_multiplier = Column(Numeric(3, 2), server_default="1.00", nullable=False)

    hall = relationship("Hall", back_populates="seats")

    __table_args__ = (
        UniqueConstraint(
            "hall_id", "row_number", "seat_number", name="uq_hall_row_seat"
        ),
    )


class Show(Base):
    __tablename__ = "shows"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    movie_id = Column(
        BigInteger, ForeignKey("movies.id", ondelete="RESTRICT"), nullable=False
    )
    hall_id = Column(
        Integer, ForeignKey("halls.id", ondelete="RESTRICT"), nullable=False
    )
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)
    base_price = Column(Numeric(10, 2), nullable=False)

    format = Column(
        Enum(FormatEnum, name="format_enum"),
        default=FormatEnum.FORMAT_2D,
        nullable=False,
    )
    status = Column(
        Enum(ShowStatusEnum, name="show_status_enum"),
        default=ShowStatusEnum.SCHEDULED,
        nullable=False,
    )

    movie = relationship("Movie", back_populates="shows")
    hall = relationship("Hall", back_populates="shows")

    __table_args__ = (
        Index("idx_shows_movie_time", "movie_id", "start_time"),
        Index("idx_shows_status_time", "status", "start_time"),
        Index("idx_shows_start_time_only", "start_time"),
    )


class Promocode(Base):
    __tablename__ = "promocodes"
    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(50), unique=True, nullable=False)
    discount_percent = Column(Integer, nullable=False)
    usage_limit = Column(Integer, nullable=True)
    usage_count = Column(Integer, server_default="0", nullable=False)
    valid_until = Column(DateTime(timezone=True), nullable=False)
    is_active = Column(Boolean, server_default="true", nullable=False)


class Order(Base):
    __tablename__ = "orders"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    promocode_id = Column(
        Integer, ForeignKey("promocodes.id", ondelete="SET NULL"), nullable=True
    )
    idempotency_key = Column(UUID(as_uuid=True), unique=True, nullable=False)
    total_price = Column(Numeric(10, 2), nullable=False)

    status = Column(
        Enum(OrderStatusEnum, name="order_status_enum"),
        default=OrderStatusEnum.PENDING,
        nullable=False,
    )
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user = relationship("User", back_populates="orders")
    transactions = relationship("Transaction", back_populates="order")
    tickets = relationship("Ticket", back_populates="order")

    __table_args__ = (
        Index("idx_orders_user_id", "user_id"),
        Index("idx_orders_created_status", "created_at", "status"),
    )


class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False)
    order_id = Column(
        BigInteger, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False
    )
    liqpay_order_id = Column(String(255), unique=True, nullable=True)
    amount = Column(Numeric(10, 2), nullable=False)

    status = Column(
        Enum(TransactionStatusEnum, name="transaction_status_enum"), nullable=False
    )
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    order = relationship("Order", back_populates="transactions")

    __table_args__ = (Index("idx_transactions_status_created", "status", "created_at"),)


class Ticket(Base):
    __tablename__ = "tickets"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    order_id = Column(
        BigInteger, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False
    )
    show_id = Column(
        BigInteger, ForeignKey("shows.id", ondelete="RESTRICT"), nullable=False
    )
    seat_id = Column(
        BigInteger, ForeignKey("seats.id", ondelete="RESTRICT"), nullable=False
    )
    price = Column(Numeric(10, 2), nullable=False)
    qr_code_hash = Column(String(255), unique=True, nullable=True)
    is_scanned = Column(Boolean, server_default="false", nullable=False)

    order = relationship("Order", back_populates="tickets")
    show = relationship("Show")
    seat = relationship("Seat")

    __table_args__ = (
        UniqueConstraint("show_id", "seat_id", name="uq_ticket_show_seat"),
        Index("idx_tickets_order", "order_id"),
        Index("idx_tickets_qr", "qr_code_hash"),
    )


class Review(Base):
    __tablename__ = "reviews"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    movie_id = Column(
        BigInteger, ForeignKey("movies.id", ondelete="CASCADE"), nullable=False
    )
    rating = Column(Integer, nullable=False)
    comment = Column(Text, nullable=True)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user = relationship("User", back_populates="reviews")
    movie = relationship("Movie", back_populates="reviews")

    __table_args__ = (
        UniqueConstraint("user_id", "movie_id", name="uq_user_movie_review"),
        Index("idx_reviews_movie_rating", "movie_id", "rating"),
    )
