from __future__ import annotations

from contextlib import asynccontextmanager

import aio_pika
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from notification.api.routes import router
from notification.db import models as _models  # noqa: F401 — registers ORM tables
from notification.events.handlers import (
    handle_order_event,
    handle_payment_event,
    handle_shipment_event,
    handle_stock_event,
)
from notification.settings import settings
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

    async def on_order_event(payload: dict) -> None:
        await handle_order_event(payload, session_factory, amqp_conn)

    async def on_payment_event(payload: dict) -> None:
        await handle_payment_event(payload, session_factory, amqp_conn)

    async def on_stock_event(payload: dict) -> None:
        await handle_stock_event(payload, session_factory, amqp_conn)

    async def on_shipment_event(payload: dict) -> None:
        await handle_shipment_event(payload, session_factory, amqp_conn)

    subscriptions = [
        ("notification_order_q", ["order.*"], on_order_event),
        ("notification_payment_q", ["payment.*"], on_payment_event),
        ("notification_stock_q", ["stock.*"], on_stock_event),
        ("notification_shipment_q", ["shipment.*"], on_shipment_event),
    ]
    consumers = []
    for queue, routing_keys, handler in subscriptions:
        consumer = MessageConsumer()
        await consumer.connect(settings.rabbitmq_url)
        await consumer.subscribe(queue, routing_keys, handler)
        await consumer.start()
        consumers.append(consumer)
    app.state.consumers = consumers

    yield

    for consumer in consumers:
        await consumer.close()
    await amqp_conn.close()
    await engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(
        title="notification-service", version="0.1.0", lifespan=lifespan
    )
    app.include_router(router)
    return app


app = create_app()
