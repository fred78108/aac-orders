"""RabbitMQ publisher and consumer using aio_pika."""
from __future__ import annotations

import json
from typing import Any, Awaitable, Callable

import aio_pika
from aio_pika import ExchangeType, Message
from aio_pika.abc import AbstractChannel, AbstractRobustConnection

_EXCHANGE = "events"


class MessagePublisher:
    """Publish domain events to RabbitMQ.

    Usage::

        publisher = MessagePublisher()
        await publisher.connect("amqp://guest:guest@localhost/")
        await publisher.publish("order.created", {"order_id": "..."})
        await publisher.close()
    """

    def __init__(self) -> None:
        self._connection: AbstractRobustConnection | None = None

    async def connect(self, url: str) -> None:
        self._connection = await aio_pika.connect_robust(url)

    async def publish(self, routing_key: str, payload: dict[str, Any]) -> None:
        if self._connection is None:
            raise RuntimeError("Not connected — call connect() first")
        async with self._connection.channel() as channel:
            exchange = await channel.declare_exchange(
                _EXCHANGE, ExchangeType.TOPIC, durable=True
            )
            await exchange.publish(
                Message(
                    json.dumps(payload).encode(),
                    content_type="application/json",
                ),
                routing_key=routing_key,
            )

    async def close(self) -> None:
        if self._connection is not None:
            await self._connection.close()
            self._connection = None


class MessageConsumer:
    """Subscribe to and process events from RabbitMQ.

    Usage::

        consumer = MessageConsumer()
        await consumer.connect("amqp://guest:guest@localhost/")
        await consumer.subscribe("payment_q", ["order.created"], handler)
        await consumer.start()
        # ... runs until close()
        await consumer.close()
    """

    def __init__(self) -> None:
        self._connection: AbstractRobustConnection | None = None
        self._channel: AbstractChannel | None = None
        self._queue: aio_pika.abc.AbstractQueue | None = None
        self._message_handler: Callable[[aio_pika.abc.AbstractIncomingMessage], Awaitable[None]] | None = None

    async def connect(self, url: str) -> None:
        self._connection = await aio_pika.connect_robust(url)

    async def subscribe(
        self,
        queue: str,
        routing_keys: list[str],
        handler: Callable[[dict[str, Any]], Awaitable[None]],
    ) -> None:
        if self._connection is None:
            raise RuntimeError("Not connected — call connect() first")
        self._channel = self._connection.channel()
        await self._channel.initialize()
        exchange = await self._channel.declare_exchange(
            _EXCHANGE, ExchangeType.TOPIC, durable=True
        )
        self._queue = await self._channel.declare_queue(queue, durable=True)
        for rk in routing_keys:
            await self._queue.bind(exchange, routing_key=rk)

        async def _on_message(message: aio_pika.abc.AbstractIncomingMessage) -> None:
            async with message.process():
                payload = json.loads(message.body.decode())
                await handler(payload)

        self._message_handler = _on_message

    async def start(self) -> None:
        if self._queue is None or self._message_handler is None:
            raise RuntimeError("Not subscribed — call subscribe() first")
        await self._queue.consume(self._message_handler)

    async def close(self) -> None:
        if self._connection is not None:
            await self._connection.close()
            self._connection = None
