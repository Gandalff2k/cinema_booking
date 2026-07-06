from enum import Enum
from pydantic_settings import BaseSettings, SettingsConfigDict


class EnvironmentType(str, Enum):
    DEVELOPMENT = "development"
    PRODUCTION = "production"
    TEST = "test"


class Settings(BaseSettings):
    DEBUG: bool = True
    DEFAULT_LOCALE: str = "uk_UA"
    ENVIRONMENT: EnvironmentType = EnvironmentType.DEVELOPMENT
    RELEASE_VERSION: str = "0.1"
    SHOW_SQL_ALCHEMY_QUERIES: int = 0

    SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 1440

    STRIPE_SECRET_KEY: str | None = None
    STRIPE_WEBHOOK_SECRET: str | None = None
    FRONTEND_URL: str = "http://localhost:8000"

    DATABASE_URL: str
    REDIS_URL: str

    @property
    def CELERY_BROKER_URL(self) -> str:
        return self.REDIS_URL

    @property
    def CELERY_BACKEND_URL(self) -> str:
        return self.REDIS_URL

    @property
    def POSTGRES_URL(self) -> str:
        return self.DATABASE_URL

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


config = Settings()
