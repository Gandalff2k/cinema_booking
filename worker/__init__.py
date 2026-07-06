from celery import Celery
from core.config import config

celery_app = Celery(
    "worker",
    backend=config.CELERY_BACKEND_URL,
    broker=config.CELERY_BROKER_URL,
    include=["worker.tasks.tickets"],
)

celery_app.conf.task_routes = {"worker.tasks.tickets.send_ticket_task": "celery"}
celery_app.conf.update(task_track_started=True)
