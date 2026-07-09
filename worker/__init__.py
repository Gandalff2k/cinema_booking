from celery import Celery

from core.config import config
from core.logging import configure_logging

configure_logging()

celery_app = Celery(
    "worker",
    backend=config.CELERY_BACKEND_URL,
    broker=config.CELERY_BROKER_URL,
    include=["worker.tasks.tickets", "worker.tasks.cache_tasks"],
)

celery_app.conf.task_routes = {"worker.tasks.tickets.send_ticket_task": "celery"}
celery_app.conf.update(
    task_track_started=True,
    # The worker runs --pool=solo (one task at a time, single process). A task
    # that hangs (e.g. a stuck SMTP/MinIO socket) would otherwise block every
    # other task forever — including the safety-critical stale-order sweep.
    # Cap every task so a hang gets killed instead of wedging the worker.
    task_time_limit=120,
    task_soft_time_limit=90,
)

# Periodic jobs (run by `celery beat`, embedded via the worker's -B flag).
celery_app.conf.beat_schedule = {
    "release-stale-orders": {
        "task": "worker.tasks.cache_tasks.release_stale_orders",
        "schedule": 60.0,  # every minute
    },
}
