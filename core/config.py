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

    LOG_TO_FILE: bool = True
    LOG_DIR: str = "logs"
    LOG_MAX_MB: int = 5
    LOG_BACKUP_COUNT: int = 3
    LOG_REQUEST_BODY: bool = True
    SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 1440

    ADMIN_EMAIL: str
    ADMIN_USERNAME: str
    ADMIN_PASSWORD: str

    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_TIMES: int = 20
    RATE_LIMIT_WINDOW_SECONDS: int = 60

    STALE_ORDER_MINUTES: int = 40

    STRIPE_SECRET_KEY: str | None = None
    STRIPE_WEBHOOK_SECRET: str | None = None
    FRONTEND_URL: str = "http://localhost:8000"

    CORS_ORIGINS: str = "*"

    EMAILS_ENABLED: bool = False
    SMTP_HOST: str | None = None
    SMTP_PORT: int = 587
    SMTP_USER: str | None = None
    SMTP_PASSWORD: str | None = None
    SMTP_TLS: bool = True
    SMTP_FROM: str = "CinemaX <no-reply@cinemax.local>"

    MINIO_ENDPOINT: str = "minio:9000"
    MINIO_BUCKET: str = "movies"
    MINIO_SECURE: bool = False

    MINIO_ROOT_USER: str
    MINIO_ROOT_PASSWORD: str

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
