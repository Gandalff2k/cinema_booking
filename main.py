import uvicorn

from core.config import config
import logging
import sys

# Налаштовуємо глобальний логер
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler("app.log", encoding="utf-8"),  # Пишемо у файл
        logging.StreamHandler(sys.stdout),
    ],
    force=True,
)

logger = logging.getLogger(__name__)
logger.info(" CinemaX API успішно запущено! Логування у файл увімкнено.")

if __name__ == "__main__":
    uvicorn.run(
        app="core.server:app",
        reload=True if config.ENVIRONMENT != "production" else False,
        workers=1,
    )
