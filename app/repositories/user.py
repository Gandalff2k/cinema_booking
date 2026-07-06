from uuid import UUID

from app.models import User
from core.repository import BaseRepository


class UserRepository(BaseRepository[User]):
    """
    User repository provides all the database operations for the User model.
    """

    async def get_by_username(
        self, username: str, join_: set[str] | None = None
    ) -> User | None:
        """
        Get user by username.
        """
        query = self._query(join_)
        query = query.filter(User.username == username)

        return await self._one_or_none(query)

    async def get_by_email(
        self, email: str, join_: set[str] | None = None
    ) -> User | None:
        """
        Get user by email.
        """
        query = self._query(join_)
        query = query.filter(User.email == email)

        return await self._one_or_none(query)

    async def get_by_contact(self, contact: str) -> User | None:
        query = self._query()
        query = query.filter((User.email == contact) | (User.phone_number == contact))

        return await self._one_or_none(query)

    async def get_by_uuid(self, uuid: UUID) -> User | None:
        query = self._query()
        query = query.filter(User.uuid == uuid)

        return await self._one_or_none(query)

    async def create_user(self, user_data: dict) -> User:
        user = User(**user_data)
        self.session.add(user)
        await self.session.flush()
        return user
