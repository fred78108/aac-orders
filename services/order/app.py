from __future__ import annotations

from contextlib import asynccontextmanager

import aio_pika
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from order.api.routes import router

# Import side-effect: registers ORM tables with Base.metadata
from order.db import models as _models  # noqa: F401
from order.settings import settings
from shared.db import Base


@asynccontextmanager
async def lifespan(app: FastAPI):
    engine = create_async_engine(settings.database_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    app.state.session_factory = async_sessionmaker(
        engine, expire_on_commit=False
    )
    app.state.amqp_conn = await aio_pika.connect_robust(settings.rabbitmq_url)

    yield

    await app.state.amqp_conn.close()
    await engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(title="order-service", version="0.1.0", lifespan=lifespan)
    app.include_router(router)
    return app


app = create_app()
