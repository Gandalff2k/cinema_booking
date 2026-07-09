import logging

from fastapi import Depends, FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware import Middleware
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from api import router
from core.cache import Cache, CustomKeyMaker, RedisBackend
from core.config import config
from core.exceptions import CustomException
from core.fastapi.dependencies import Logging
from core.fastapi.middlewares import ResponseLoggerMiddleware, SQLAlchemyMiddleware
from core.logging import configure_logging

logger = logging.getLogger(__name__)


def init_routers(app_: FastAPI) -> None:
    app_.include_router(router)


def init_listeners(app_: FastAPI) -> None:
    @app_.exception_handler(CustomException)
    async def custom_exception_handler(request: Request, exc: CustomException):
        logger.warning(
            "%s on %s %s: %s",
            type(exc).__name__,
            request.method,
            request.url.path,
            exc.message,
        )
        return JSONResponse(
            status_code=int(exc.code),
            content={"error_code": int(exc.error_code), "message": exc.message},
        )

    @app_.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ):
        details = [
            {
                "field": ".".join(str(p) for p in err.get("loc", [])),
                "message": err.get("msg"),
            }
            for err in exc.errors()
        ]
        return JSONResponse(
            status_code=422,
            content=jsonable_encoder(
                {"error_code": 422, "message": "Invalid data", "detail": details}
            ),
        )

    @app_.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=500,
            content={"error_code": 500, "message": "Internal server error"},
        )


def make_middleware() -> list[Middleware]:
    origins = (
        ["*"]
        if config.CORS_ORIGINS == "*"
        else [origin.strip() for origin in config.CORS_ORIGINS.split(",")]
    )
    middleware = [
        Middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=False,
            allow_methods=["*"],
            allow_headers=["*"],
        ),
        Middleware(SQLAlchemyMiddleware),
        Middleware(ResponseLoggerMiddleware),
    ]
    return middleware


def init_cache() -> None:
    Cache.init(backend=RedisBackend(), key_maker=CustomKeyMaker())


def create_app() -> FastAPI:
    configure_logging()
    app_ = FastAPI(
        title="Booking service API",
        version="1.0.0",
        docs_url=None if config.ENVIRONMENT == "production" else "/docs",
        redoc_url=None if config.ENVIRONMENT == "production" else "/redoc",
        dependencies=[Depends(Logging)],
        middleware=make_middleware(),
    )
    init_routers(app_=app_)
    init_listeners(app_=app_)
    init_cache()
    return app_


app = create_app()

app.mount("/frontend", StaticFiles(directory="frontend"), name="frontend")


@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/frontend/pages/home/index.html")
