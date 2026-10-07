from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db import engine, init_db
from app.routers.payments import router as payments_router
from app.routers.tariffs import router as tariffs_router
from app.routers.webhooks import router as webhooks_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db(engine)
    yield


def create_app() -> FastAPI:
    application = FastAPI(title="Kvitto Payments", lifespan=lifespan)
    application.include_router(tariffs_router)
    application.include_router(payments_router)
    application.include_router(webhooks_router)
    return application


app = create_app()
