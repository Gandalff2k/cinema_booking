from functools import partial

from fastapi import Depends

from app.controllers import AuthController, UserController
from app.models import Cinema, Movie, Seat, User
from app.repositories import BookingRepository, CinemaRepository, UserRepository
from core.database import get_session


class Factory:
    """
    This is the factory container that will instantiate all the controllers and
    repositories which can be accessed by the rest of the application.
    """

    # Repositories
    user_repository = partial(UserRepository, User)
    cinema_repository = partial(CinemaRepository, Movie)
    booking_repository = partial(BookingRepository, Seat)

    def get_user_controller(self, db_session=Depends(get_session)):
        return UserController(
            user_repository=self.user_repository(db_session=db_session)
        )

    def get_auth_controller(self, db_session=Depends(get_session)):
        return AuthController(
            user_repository=self.user_repository(db_session=db_session),
        )

    def get_cinema_repository(self, db_session=Depends(get_session)):
        return self.cinema_repository(db_session=db_session)

    def get_booking_repository(self, db_session=Depends(get_session)):
        return self.booking_repository(db_session=db_session)
