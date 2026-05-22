from __future__ import annotations

from contextlib import asynccontextmanager

import aio_pika
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from shipping.api.routes import router
from shipping.db import models as _models  # noqa: F401 — registers ORM tables
from shipping.events.handlers import handle_order_packed
from shipping.settings import settings
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

    async def on_order_packed(payload: dict) -> None:
        await handle_order_packed(payload, session_factory, amqp_conn)

    consumer = MessageConsumer()
    await consumer.connect(settings.rabbitmq_url)
    await consumer.subscribe(
        "shipping_order_packed_q", ["order.packed"], on_order_packed
    )
    await consumer.start()
    app.state.consumer = consumer

    yield

    await consumer.close()
    await amqp_conn.close()
    await engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(title="shipping-service", version="0.1.0", lifespan=lifespan)
    app.include_router(router)
    return app


app = create_app()
