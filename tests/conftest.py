import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-do-not-use-in-prod")
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:password123@localhost:5432/cinema_test",
)
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/1")
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("EMAILS_ENABLED", "False")
os.environ.setdefault("RATE_LIMIT_ENABLED", "False")

os.environ.setdefault("RATE_LIMIT_TIMES", "3")
os.environ.setdefault("RATE_LIMIT_WINDOW_SECONDS", "60")
os.environ.setdefault("JWT_EXPIRE_MINUTES", "60")


os.environ.setdefault("ADMIN_EMAIL", "admin@test.local")
os.environ.setdefault("ADMIN_USERNAME", "test_admin")
os.environ.setdefault("ADMIN_PASSWORD", "test-admin-password")
os.environ.setdefault("MINIO_ROOT_USER", "test_minio")
os.environ.setdefault("MINIO_ROOT_PASSWORD", "test-minio-password")
