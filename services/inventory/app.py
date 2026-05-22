from __future__ import annotations

from contextlib import asynccontextmanager

import aio_pika
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from inventory.api.routes import router
from inventory.db import models as _models  # noqa: F401 — registers ORM tables
from inventory.events.handlers import handle_payment_captured
from inventory.settings import settings
from shared.db import Base
from shared.messaging import MessageConsumer


@asynccontextmanager
async def lifespan(app: FastAPI):
    engine = create_async_engine(settings.database_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    app.state.session_factory = session_factory

    amqp_conn = await aio_pika.connect_robust(settings.rabbitmq_url)
    app.state.amqp_conn = amqp_conn

    async def on_payment_captured(payload: dict) -> None:
        await handle_payment_captured(payload, session_factory, amqp_conn)

    consumer = MessageConsumer()
    await consumer.connect(settings.rabbitmq_url)
    await consumer.subscribe(
        "inventory_payment_captured_q",
        ["payment.captured"],
        on_payment_captured,
    )
    await consumer.start()
    app.state.consumer = consumer

    yield

    await consumer.close()
    await amqp_conn.close()
    await engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(
        title="inventory-service", version="0.1.0", lifespan=lifespan
    )
    app.include_router(router)
    return app


app = create_app()
