from __future__ import annotations

from contextlib import asynccontextmanager

import aio_pika
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from fulfillment.api.routes import router
from fulfillment.db import models as _models  # noqa: F401 — registers ORM tables
from fulfillment.events.handlers import (
    handle_shipment_failed,
    handle_stock_reserved,
)
from fulfillment.settings import settings
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

    async def on_stock_reserved(payload: dict) -> None:
        await handle_stock_reserved(payload, session_factory, amqp_conn)

    async def on_shipment_failed(payload: dict) -> None:
        await handle_shipment_failed(payload, session_factory, amqp_conn)

    consumer_stock = MessageConsumer()
    await consumer_stock.connect(settings.rabbitmq_url)
    await consumer_stock.subscribe(
        "fulfillment_stock_reserved_q", ["stock.reserved"], on_stock_reserved
    )
    await consumer_stock.start()
    app.state.consumer_stock = consumer_stock

    consumer_shipment = MessageConsumer()
    await consumer_shipment.connect(settings.rabbitmq_url)
    await consumer_shipment.subscribe(
        "fulfillment_shipment_failed_q",
        ["shipment.failed"],
        on_shipment_failed,
    )
    await consumer_shipment.start()
    app.state.consumer_shipment = consumer_shipment

    yield

    await consumer_stock.close()
    await consumer_shipment.close()
    await amqp_conn.close()
    await engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(
        title="fulfillment-service", version="0.1.0", lifespan=lifespan
    )
    app.include_router(router)
    return app


app = create_app()
