import logging
import os
import sys
from logging.handlers import RotatingFileHandler

from core.config import config

_LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"


def configure_logging() -> None:
    level = logging.DEBUG if config.DEBUG else logging.INFO

    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]

    if config.LOG_TO_FILE:
        os.makedirs(config.LOG_DIR, exist_ok=True)
        file_handler = RotatingFileHandler(
            filename=os.path.join(config.LOG_DIR, "app.log"),
            maxBytes=config.LOG_MAX_MB * 1024 * 1024,
            backupCount=config.LOG_BACKUP_COUNT,
            encoding="utf-8",
        )
        handlers.append(file_handler)

    logging.basicConfig(
        level=level,
        format=_LOG_FORMAT,
        handlers=handlers,
        force=True,
    )

    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.INFO if config.SHOW_SQL_ALCHEMY_QUERIES else logging.WARNING
    )

    for noisy in ("celery", "kombu", "amqp"):
        logging.getLogger(noisy).setLevel(logging.INFO)
