import logging

import uvicorn

from core.config import config
from core.logging import configure_logging

configure_logging()
logger = logging.getLogger(__name__)
logger.info("CinemaX API запускається...")

if __name__ == "__main__":
    uvicorn.run(
        app="core.server:app",
        reload=True if config.ENVIRONMENT != "production" else False,
        workers=1,
    )
