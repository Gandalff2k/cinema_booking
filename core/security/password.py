from passlib.context import CryptContext

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


class PasswordHandler:
    @staticmethod
    def hash(password: str) -> str:
        return get_password_hash(password)

    @staticmethod
    def verify(hashed_password: str, plain_password: str) -> bool:
        return verify_password(plain_password, hashed_password)
