from fastapi import APIRouter

from app.controllers.payments import payments_router
from api.v1.auth import auth_router
from api.v1.booking import booking_router
from api.v1.monitoring import monitoring_router
from api.v1.movies import movies_router
from api.v1.users import users_router
from api.v1.users.users import reviews_router, movies_admin_router

v1_router = APIRouter()
v1_router.include_router(auth_router)
v1_router.include_router(movies_router)
v1_router.include_router(booking_router)
v1_router.include_router(payments_router)
v1_router.include_router(monitoring_router, prefix="/monitoring")
v1_router.include_router(users_router, prefix="/users")
v1_router.include_router(movies_admin_router)
v1_router.include_router(reviews_router)
