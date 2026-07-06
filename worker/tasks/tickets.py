import asyncio
from worker import celery_app
from core.database import standalone_session, session
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from app.models import Order, Ticket


# 1. Створюємо асинхронну функцію і вішаємо ТВІЙ декоратор
@standalone_session
async def _process_ticket(order_id: int):
    # Тут твій session вже має правильний контекст завдяки декоратору!
    query = (
        select(Order)
        .options(joinedload(Order.tickets).joinedload(Ticket.seat))
        .where(Order.id == order_id)
    )
    result = await session.execute(query)
    order = result.unique().scalar_one_or_none()

    if not order:
        return

    # Тут логіка генерації квитка та відправки email
    # ...
    print(f"Квитки для замовлення {order_id} успішно згенеровано і відправлено!")


# 2. Створюємо синхронну обгортку для Celery
@celery_app.task(name="worker.tasks.tickets.send_ticket_task")
def send_ticket_task(order_id: int):
    # Запускаємо асинхронний код в Event Loop
    asyncio.run(_process_ticket(order_id))
