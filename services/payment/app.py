from __future__ import annotations

from contextlib import asynccontextmanager

import aio_pika
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from payment.api.routes import router
from payment.db import models as _models  # noqa: F401 — registers ORM tables
from payment.events.handlers import handle_order_created, handle_stock_insufficient
from payment.settings import settings
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

    async def on_order_created(payload: dict) -> None:
        await handle_order_created(payload, session_factory, amqp_conn)

    async def on_stock_insufficient(payload: dict) -> None:
        await handle_stock_insufficient(payload, session_factory, amqp_conn)

    consumer_order = MessageConsumer()
    await consumer_order.connect(settings.rabbitmq_url)
    await consumer_order.subscribe(
        "payment_order_created_q", ["order.created"], on_order_created
    )
    await consumer_order.start()
    app.state.consumer_order = consumer_order

    consumer_stock = MessageConsumer()
    await consumer_stock.connect(settings.rabbitmq_url)
    await consumer_stock.subscribe(
        "payment_stock_insufficient_q", ["stock.insufficient"], on_stock_insufficient
    )
    await consumer_stock.start()
    app.state.consumer_stock = consumer_stock

    yield

    await consumer_order.close()
    await consumer_stock.close()
    await amqp_conn.close()
    await engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(title="payment-service", version="0.1.0", lifespan=lifespan)
    app.include_router(router)
    return app


app = create_app()
