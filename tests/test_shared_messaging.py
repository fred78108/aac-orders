"""Unit tests for shared.messaging — MessagePublisher and MessageConsumer.

All RabbitMQ I/O is mocked so the suite runs without a broker.
"""
from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from shared.messaging import MessagePublisher, MessageConsumer

AMQP_URL = "amqp://guest:guest@localhost:5672/"


# ── Helpers ──────────────────────────────────────────────────────────────────


def _make_publisher_mocks() -> tuple[Any, Any, Any]:
    """Return (mock_conn, mock_channel, mock_exchange) wired for MessagePublisher.

    conn.channel() is synchronous in aio_pika and returns an async context
    manager, so mock_channel implements __aenter__/__aexit__ directly.
    """
    mock_exchange = AsyncMock()
    mock_channel = AsyncMock()
    mock_channel.declare_exchange = AsyncMock(return_value=mock_exchange)
    mock_channel.__aenter__ = AsyncMock(return_value=mock_channel)
    mock_channel.__aexit__ = AsyncMock(return_value=None)

    mock_conn = AsyncMock()
    mock_conn.channel = MagicMock(return_value=mock_channel)  # sync call

    return mock_conn, mock_channel, mock_exchange


def _make_incoming_message(payload: dict) -> Any:
    """Return a mock IncomingMessage whose process() is a sync-returning async CM."""
    process_ctx = AsyncMock()
    process_ctx.__aenter__ = AsyncMock(return_value=None)
    process_ctx.__aexit__ = AsyncMock(return_value=False)

    mock_message = MagicMock()
    mock_message.body = json.dumps(payload).encode()
    mock_message.process = MagicMock(return_value=process_ctx)
    return mock_message


def _make_consumer_mocks() -> tuple[Any, Any, Any, Any]:
    """Return (mock_conn, mock_channel, mock_exchange, mock_queue) for MessageConsumer."""
    mock_exchange = AsyncMock()
    mock_queue = AsyncMock()
    mock_channel = AsyncMock()
    mock_channel.initialize = AsyncMock()
    mock_channel.declare_exchange = AsyncMock(return_value=mock_exchange)
    mock_channel.declare_queue = AsyncMock(return_value=mock_queue)

    mock_conn = AsyncMock()
    mock_conn.channel = MagicMock(return_value=mock_channel)  # sync call

    return mock_conn, mock_channel, mock_exchange, mock_queue


# ── MessagePublisher.connect ──────────────────────────────────────────────────


class TestMessagePublisherConnect:
    async def test_connect_calls_connect_robust(self) -> None:
        publisher = MessagePublisher()
        with patch("shared.messaging.aio_pika.connect_robust", new_callable=AsyncMock) as mock_cr:
            await publisher.connect(AMQP_URL)
        mock_cr.assert_called_once_with(AMQP_URL)

    async def test_connect_stores_connection(self) -> None:
        mock_conn = AsyncMock()
        publisher = MessagePublisher()
        with patch("shared.messaging.aio_pika.connect_robust", return_value=mock_conn):
            await publisher.connect(AMQP_URL)
        assert publisher._connection is mock_conn

    async def test_initial_connection_is_none(self) -> None:
        assert MessagePublisher()._connection is None


# ── MessagePublisher.publish ──────────────────────────────────────────────────


class TestMessagePublisherPublish:
    async def test_publish_before_connect_raises(self) -> None:
        publisher = MessagePublisher()
        with pytest.raises(RuntimeError, match="connect"):
            await publisher.publish("order.created", {"order_id": "x"})

    async def test_publish_opens_channel(self) -> None:
        mock_conn, mock_channel, _ = _make_publisher_mocks()
        publisher = MessagePublisher()
        with patch("shared.messaging.aio_pika.connect_robust", return_value=mock_conn):
            await publisher.connect(AMQP_URL)
        await publisher.publish("order.created", {})
        mock_conn.channel.assert_called_once()

    async def test_publish_declares_topic_exchange_named_events(self) -> None:
        from aio_pika import ExchangeType

        mock_conn, mock_channel, _ = _make_publisher_mocks()
        publisher = MessagePublisher()
        with patch("shared.messaging.aio_pika.connect_robust", return_value=mock_conn):
            await publisher.connect(AMQP_URL)
        await publisher.publish("order.created", {})

        mock_channel.declare_exchange.assert_called_once()
        args, kwargs = mock_channel.declare_exchange.call_args
        assert args[0] == "events"
        assert args[1] == ExchangeType.TOPIC
        assert kwargs.get("durable") is True

    async def test_publish_sends_json_body(self) -> None:
        mock_conn, _, mock_exchange = _make_publisher_mocks()
        publisher = MessagePublisher()
        with patch("shared.messaging.aio_pika.connect_robust", return_value=mock_conn):
            await publisher.connect(AMQP_URL)

        payload = {"order_id": "abc-123", "total_cents": 9999}
        await publisher.publish("order.created", payload)

        mock_exchange.publish.assert_called_once()
        msg_arg = mock_exchange.publish.call_args[0][0]
        assert json.loads(msg_arg.body.decode()) == payload

    async def test_publish_uses_routing_key(self) -> None:
        mock_conn, _, mock_exchange = _make_publisher_mocks()
        publisher = MessagePublisher()
        with patch("shared.messaging.aio_pika.connect_robust", return_value=mock_conn):
            await publisher.connect(AMQP_URL)
        await publisher.publish("payment.captured", {"x": 1})

        _, kwargs = mock_exchange.publish.call_args
        assert kwargs.get("routing_key") == "payment.captured"

    async def test_publish_content_type_is_json(self) -> None:
        mock_conn, _, mock_exchange = _make_publisher_mocks()
        publisher = MessagePublisher()
        with patch("shared.messaging.aio_pika.connect_robust", return_value=mock_conn):
            await publisher.connect(AMQP_URL)
        await publisher.publish("stock.reserved", {"reservation_id": "r1"})

        msg_arg = mock_exchange.publish.call_args[0][0]
        assert msg_arg.content_type == "application/json"

    async def test_publish_all_saga_routing_keys(self) -> None:
        """publish() accepts every routing key used in the saga."""
        routing_keys = [
            "order.created",
            "payment.captured",
            "payment.failed",
            "payment.refund_requested",
            "stock.reserved",
            "stock.insufficient",
            "order.packed",
            "shipment.dispatched",
            "shipment.failed",
            "order.return_initiated",
        ]
        for rk in routing_keys:
            mock_conn, _, mock_exchange = _make_publisher_mocks()
            publisher = MessagePublisher()
            with patch("shared.messaging.aio_pika.connect_robust", return_value=mock_conn):
                await publisher.connect(AMQP_URL)
            await publisher.publish(rk, {})
            _, kwargs = mock_exchange.publish.call_args
            assert kwargs.get("routing_key") == rk

    async def test_publish_empty_payload(self) -> None:
        mock_conn, _, mock_exchange = _make_publisher_mocks()
        publisher = MessagePublisher()
        with patch("shared.messaging.aio_pika.connect_robust", return_value=mock_conn):
            await publisher.connect(AMQP_URL)
        await publisher.publish("order.created", {})
        msg_arg = mock_exchange.publish.call_args[0][0]
        assert json.loads(msg_arg.body.decode()) == {}

    async def test_publish_complex_payload_roundtrips(self) -> None:
        import uuid

        mock_conn, _, mock_exchange = _make_publisher_mocks()
        publisher = MessagePublisher()
        with patch("shared.messaging.aio_pika.connect_robust", return_value=mock_conn):
            await publisher.connect(AMQP_URL)

        payload = {"order_id": str(uuid.uuid4()), "total_cents": 4999, "items": [1, 2, 3]}
        await publisher.publish("order.created", payload)
        msg_arg = mock_exchange.publish.call_args[0][0]
        assert json.loads(msg_arg.body.decode()) == payload


# ── MessagePublisher.close ────────────────────────────────────────────────────


class TestMessagePublisherClose:
    async def test_close_calls_connection_close(self) -> None:
        mock_conn = AsyncMock()
        publisher = MessagePublisher()
        with patch("shared.messaging.aio_pika.connect_robust", return_value=mock_conn):
            await publisher.connect(AMQP_URL)
        await publisher.close()
        mock_conn.close.assert_called_once()

    async def test_close_clears_connection_reference(self) -> None:
        mock_conn = AsyncMock()
        publisher = MessagePublisher()
        with patch("shared.messaging.aio_pika.connect_robust", return_value=mock_conn):
            await publisher.connect(AMQP_URL)
        await publisher.close()
        assert publisher._connection is None

    async def test_close_without_connect_is_noop(self) -> None:
        publisher = MessagePublisher()
        await publisher.close()  # must not raise

    async def test_close_twice_does_not_raise(self) -> None:
        mock_conn = AsyncMock()
        publisher = MessagePublisher()
        with patch("shared.messaging.aio_pika.connect_robust", return_value=mock_conn):
            await publisher.connect(AMQP_URL)
        await publisher.close()
        await publisher.close()  # second close is a no-op


# ── MessageConsumer.connect ───────────────────────────────────────────────────


class TestMessageConsumerConnect:
    async def test_connect_calls_connect_robust(self) -> None:
        consumer = MessageConsumer()
        with patch("shared.messaging.aio_pika.connect_robust", new_callable=AsyncMock) as mock_cr:
            await consumer.connect(AMQP_URL)
        mock_cr.assert_called_once_with(AMQP_URL)

    async def test_connect_stores_connection(self) -> None:
        mock_conn = AsyncMock()
        consumer = MessageConsumer()
        with patch("shared.messaging.aio_pika.connect_robust", return_value=mock_conn):
            await consumer.connect(AMQP_URL)
        assert consumer._connection is mock_conn

    async def test_initial_state_is_unconnected(self) -> None:
        c = MessageConsumer()
        assert c._connection is None
        assert c._channel is None
        assert c._queue is None


# ── MessageConsumer.subscribe ─────────────────────────────────────────────────


class TestMessageConsumerSubscribe:
    async def test_subscribe_before_connect_raises(self) -> None:
        consumer = MessageConsumer()
        with pytest.raises(RuntimeError, match="connect"):
            await consumer.subscribe("q", ["order.created"], AsyncMock())

    async def test_subscribe_calls_channel(self) -> None:
        mock_conn, mock_channel, _, _ = _make_consumer_mocks()
        consumer = MessageConsumer()
        with patch("shared.messaging.aio_pika.connect_robust", return_value=mock_conn):
            await consumer.connect(AMQP_URL)
        await consumer.subscribe("payment_q", ["order.created"], AsyncMock())
        mock_conn.channel.assert_called_once()

    async def test_subscribe_initializes_channel(self) -> None:
        mock_conn, mock_channel, _, _ = _make_consumer_mocks()
        consumer = MessageConsumer()
        with patch("shared.messaging.aio_pika.connect_robust", return_value=mock_conn):
            await consumer.connect(AMQP_URL)
        await consumer.subscribe("payment_q", ["order.created"], AsyncMock())
        mock_channel.initialize.assert_called_once()

    async def test_subscribe_declares_durable_topic_exchange(self) -> None:
        from aio_pika import ExchangeType

        mock_conn, mock_channel, _, _ = _make_consumer_mocks()
        consumer = MessageConsumer()
        with patch("shared.messaging.aio_pika.connect_robust", return_value=mock_conn):
            await consumer.connect(AMQP_URL)
        await consumer.subscribe("inventory_q", ["payment.captured"], AsyncMock())

        mock_channel.declare_exchange.assert_called_once()
        args, kwargs = mock_channel.declare_exchange.call_args
        assert args[0] == "events"
        assert args[1] == ExchangeType.TOPIC
        assert kwargs.get("durable") is True

    async def test_subscribe_declares_durable_queue(self) -> None:
        mock_conn, mock_channel, _, _ = _make_consumer_mocks()
        consumer = MessageConsumer()
        with patch("shared.messaging.aio_pika.connect_robust", return_value=mock_conn):
            await consumer.connect(AMQP_URL)
        await consumer.subscribe("fulfillment_q", ["stock.reserved"], AsyncMock())

        mock_channel.declare_queue.assert_called_once_with("fulfillment_q", durable=True)

    async def test_subscribe_binds_single_routing_key(self) -> None:
        mock_conn, _, mock_exchange, mock_queue = _make_consumer_mocks()
        consumer = MessageConsumer()
        with patch("shared.messaging.aio_pika.connect_robust", return_value=mock_conn):
            await consumer.connect(AMQP_URL)
        await consumer.subscribe("shipping_q", ["order.packed"], AsyncMock())

        mock_queue.bind.assert_called_once_with(mock_exchange, routing_key="order.packed")

    async def test_subscribe_binds_multiple_routing_keys(self) -> None:
        mock_conn, _, mock_exchange, mock_queue = _make_consumer_mocks()
        consumer = MessageConsumer()
        with patch("shared.messaging.aio_pika.connect_robust", return_value=mock_conn):
            await consumer.connect(AMQP_URL)

        routing_keys = ["order.created", "stock.insufficient"]
        await consumer.subscribe("payment_q", routing_keys, AsyncMock())

        assert mock_queue.bind.call_count == 2
        bound = {c.kwargs["routing_key"] for c in mock_queue.bind.call_args_list}
        assert bound == set(routing_keys)

    async def test_subscribe_notification_wildcard_keys(self) -> None:
        """notification-service uses wildcard bindings across four namespaces."""
        mock_conn, _, mock_exchange, mock_queue = _make_consumer_mocks()
        consumer = MessageConsumer()
        with patch("shared.messaging.aio_pika.connect_robust", return_value=mock_conn):
            await consumer.connect(AMQP_URL)

        wildcards = ["order.*", "payment.*", "stock.*", "shipment.*"]
        await consumer.subscribe("notification_q", wildcards, AsyncMock())

        assert mock_queue.bind.call_count == 4
        bound = {c.kwargs["routing_key"] for c in mock_queue.bind.call_args_list}
        assert bound == set(wildcards)

    async def test_subscribe_stores_queue_reference(self) -> None:
        mock_conn, _, _, mock_queue = _make_consumer_mocks()
        consumer = MessageConsumer()
        with patch("shared.messaging.aio_pika.connect_robust", return_value=mock_conn):
            await consumer.connect(AMQP_URL)
        await consumer.subscribe("q", ["order.created"], AsyncMock())
        assert consumer._queue is mock_queue

    async def test_subscribe_stores_channel_reference(self) -> None:
        mock_conn, mock_channel, _, _ = _make_consumer_mocks()
        consumer = MessageConsumer()
        with patch("shared.messaging.aio_pika.connect_robust", return_value=mock_conn):
            await consumer.connect(AMQP_URL)
        await consumer.subscribe("q", ["order.created"], AsyncMock())
        assert consumer._channel is mock_channel


# ── MessageConsumer.start ─────────────────────────────────────────────────────


class TestMessageConsumerStart:
    async def test_start_before_subscribe_raises(self) -> None:
        consumer = MessageConsumer()
        with patch("shared.messaging.aio_pika.connect_robust", return_value=AsyncMock()):
            await consumer.connect(AMQP_URL)
        with pytest.raises(RuntimeError, match="subscribe"):
            await consumer.start()

    async def test_start_without_connect_raises(self) -> None:
        consumer = MessageConsumer()
        with pytest.raises(RuntimeError):
            await consumer.start()

    async def test_start_calls_queue_consume(self) -> None:
        mock_conn, _, _, mock_queue = _make_consumer_mocks()
        consumer = MessageConsumer()
        with patch("shared.messaging.aio_pika.connect_robust", return_value=mock_conn):
            await consumer.connect(AMQP_URL)
        handler = AsyncMock()
        await consumer.subscribe("q", ["order.created"], handler)
        await consumer.start()
        mock_queue.consume.assert_called_once()

    async def test_start_passes_message_handler_to_consume(self) -> None:
        mock_conn, _, _, mock_queue = _make_consumer_mocks()
        consumer = MessageConsumer()
        with patch("shared.messaging.aio_pika.connect_robust", return_value=mock_conn):
            await consumer.connect(AMQP_URL)
        await consumer.subscribe("q", ["order.created"], AsyncMock())
        await consumer.start()

        consumed_cb = mock_queue.consume.call_args[0][0]
        assert consumed_cb is consumer._message_handler


# ── MessageConsumer: message handler dispatching ──────────────────────────────


class TestMessageConsumerHandler:
    async def test_handler_receives_deserialized_payload(self) -> None:
        """The internal _on_message function deserializes JSON and calls the user handler."""
        mock_conn, _, _, mock_queue = _make_consumer_mocks()
        consumer = MessageConsumer()
        with patch("shared.messaging.aio_pika.connect_robust", return_value=mock_conn):
            await consumer.connect(AMQP_URL)

        received: list[dict] = []

        async def user_handler(payload: dict) -> None:
            received.append(payload)

        await consumer.subscribe("q", ["order.created"], user_handler)
        await consumer.start()

        payload = {"order_id": "test-123", "total_cents": 500}
        on_message = mock_queue.consume.call_args[0][0]
        await on_message(_make_incoming_message(payload))

        assert received == [payload]

    async def test_handler_calls_message_process_context(self) -> None:
        """_on_message must use message.process() to ack/nack automatically."""
        mock_conn, _, _, mock_queue = _make_consumer_mocks()
        consumer = MessageConsumer()
        with patch("shared.messaging.aio_pika.connect_robust", return_value=mock_conn):
            await consumer.connect(AMQP_URL)

        await consumer.subscribe("q", ["order.created"], AsyncMock())
        await consumer.start()

        mock_message = _make_incoming_message({})
        on_message = mock_queue.consume.call_args[0][0]
        await on_message(mock_message)

        mock_message.process.assert_called_once()

    async def test_handler_propagates_user_handler_call(self) -> None:
        mock_conn, _, _, mock_queue = _make_consumer_mocks()
        consumer = MessageConsumer()
        with patch("shared.messaging.aio_pika.connect_robust", return_value=mock_conn):
            await consumer.connect(AMQP_URL)

        user_handler = AsyncMock()
        await consumer.subscribe("q", ["stock.reserved"], user_handler)
        await consumer.start()

        payload = {"reservation_id": "r-999"}
        on_message = mock_queue.consume.call_args[0][0]
        await on_message(_make_incoming_message(payload))

        user_handler.assert_awaited_once_with(payload)


# ── MessageConsumer.close ─────────────────────────────────────────────────────


class TestMessageConsumerClose:
    async def test_close_calls_connection_close(self) -> None:
        mock_conn = AsyncMock()
        consumer = MessageConsumer()
        with patch("shared.messaging.aio_pika.connect_robust", return_value=mock_conn):
            await consumer.connect(AMQP_URL)
        await consumer.close()
        mock_conn.close.assert_called_once()

    async def test_close_clears_connection_reference(self) -> None:
        mock_conn = AsyncMock()
        consumer = MessageConsumer()
        with patch("shared.messaging.aio_pika.connect_robust", return_value=mock_conn):
            await consumer.connect(AMQP_URL)
        await consumer.close()
        assert consumer._connection is None

    async def test_close_without_connect_is_noop(self) -> None:
        consumer = MessageConsumer()
        await consumer.close()  # must not raise

    async def test_close_twice_does_not_raise(self) -> None:
        mock_conn = AsyncMock()
        consumer = MessageConsumer()
        with patch("shared.messaging.aio_pika.connect_robust", return_value=mock_conn):
            await consumer.connect(AMQP_URL)
        await consumer.close()
        await consumer.close()
