"""
Tests for the shipping-service bounded context.

shipping-service is step 5 of the happy-path saga: it subscribes
to order.packed, integrates with an external carrier to generate
a shipping label, and publishes shipment.dispatched — the final
event in the main happy-path chain.

If the carrier call fails, shipping-service emits shipment.failed,
which triggers the order.return_initiated compensating event from
fulfillment-service.

Responsibilities verified here:
  - Present in every architecture diagram
  - Assigned port :8005 and dedicated shipping_db (:5436)
  - Subscribes to order.packed
  - Publishes shipment.dispatched (terminal happy-path event)
  - Failure condition: shipment.failed documented
  - Domain model: Shipment dataclass
  - ORM model: ShipmentRow table mapping
  - Repository: save, get, update_status
  - Publishers: correct routing keys and payload shape
  - Handler: saga logic for order.packed
  - App: FastAPI app structure and health endpoint
"""

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from shipping.app import create_app
from shipping.db.models import ShipmentRow
from shipping.db.repository import ShipmentRepository
from shipping.domain.models import Shipment, ShipmentStatus
from shipping.events.handlers import handle_order_packed
from shipping.events.publishers import (
    publish_shipment_dispatched,
    publish_shipment_failed,
)
from shared.events import ShipmentDispatchedEvent, ShipmentFailedEvent


# ---------------------------------------------------------------------------
# Architecture / diagram tests (unchanged)
# ---------------------------------------------------------------------------


class TestShippingServiceDiagramPresence:
    """shipping-service must appear in all relevant diagrams."""

    def test_in_service_overview(self, service_overview_src: str) -> None:
        """shipping-service must be in service_overview.py."""
        assert "shipping-service" in service_overview_src

    def test_in_deployment(self, deployment_src: str) -> None:
        """shipping-service must be defined in deployment.py."""
        assert "shipping-service" in deployment_src

    def test_in_event_flow(self, event_flow_src: str) -> None:
        """shipping-service must be defined in event_flow.py."""
        assert "shipping-service" in event_flow_src

    def test_service_cluster_in_service_overview(
        self, service_overview_src: str
    ) -> None:
        """A dedicated 'Shipping Service' cluster must exist."""
        assert "Shipping Service" in service_overview_src


class TestShippingServicePorts:
    """shipping-service must use the correct assigned ports."""

    def test_service_port_8005(self, deployment_src: str) -> None:
        """shipping-service must be assigned port 8005."""
        assert ":8005" in deployment_src

    def test_database_container_name(self, deployment_src: str) -> None:
        """The paired DB container must be postgres-shipping."""
        assert "postgres-shipping" in deployment_src

    def test_database_port_5436(self, deployment_src: str) -> None:
        """shipping_db must be on port 5436."""
        assert ":5436" in deployment_src

    def test_database_name_in_service_overview(
        self, service_overview_src: str
    ) -> None:
        """shipping_db must appear paired with shipping-service."""
        assert "shipping_db" in service_overview_src


class TestShippingServiceEvents:
    """shipping-service event subscription and publishing rules."""

    def test_subscribes_to_order_packed(self, event_flow_src: str) -> None:
        """shipping-service must subscribe to order.packed."""
        assert "order.packed" in event_flow_src
        assert "shipping_svc" in event_flow_src

    def test_publishes_shipment_dispatched(self, event_flow_src: str) -> None:
        """shipping-service must publish shipment.dispatched."""
        assert "shipment.dispatched" in event_flow_src

    def test_shipment_dispatched_is_final_happy_path_event(
        self, event_flow_src: str
    ) -> None:
        """shipment.dispatched must be the last saga event."""
        pos = event_flow_src.index("shipment.dispatched")
        for earlier_event in [
            "order.created",
            "payment.captured",
            "stock.reserved",
            "order.packed",
        ]:
            assert event_flow_src.index(earlier_event) < pos, (
                f"{earlier_event} should precede shipment.dispatched"
            )

    def test_shipment_dispatched_follows_order_packed(
        self, event_flow_src: str
    ) -> None:
        """shipment.dispatched must appear after order.packed."""
        assert event_flow_src.index("order.packed") < (
            event_flow_src.index("shipment.dispatched")
        )


class TestShippingServiceCompensation:
    """shipping-service failure condition must be documented."""

    def test_shipment_failed_in_readme(self, arch_readme: str) -> None:
        """shipment.failed must appear in the README."""
        assert "shipment.failed" in arch_readme

    def test_shipment_failure_triggers_return_initiated(
        self, arch_readme: str
    ) -> None:
        """README must link shipment.failed to order.return_initiated."""
        assert "shipment.failed" in arch_readme
        assert "order.return_initiated" in arch_readme


# ---------------------------------------------------------------------------
# Domain model
# ---------------------------------------------------------------------------


class TestShipmentDomainModel:
    """Shipment dataclass behaviour."""

    def test_id_is_auto_generated(self) -> None:
        s1 = Shipment(order_id=uuid4(), carrier="DHL", tracking_number="AAA")
        s2 = Shipment(order_id=uuid4(), carrier="UPS", tracking_number="BBB")
        assert s1.id != s2.id

    def test_default_status_is_pending(self) -> None:
        s = Shipment(order_id=uuid4(), carrier="DHL", tracking_number="TRK1")
        assert s.status == ShipmentStatus.PENDING

    def test_fields_set_correctly(self) -> None:
        oid = uuid4()
        s = Shipment(order_id=oid, carrier="FedEx", tracking_number="XYZ123")
        assert s.order_id == oid
        assert s.carrier == "FedEx"
        assert s.tracking_number == "XYZ123"


# ---------------------------------------------------------------------------
# ORM model
# ---------------------------------------------------------------------------


class TestShipmentRowORM:
    """ShipmentRow SQLAlchemy mapping."""

    def test_tablename(self) -> None:
        assert ShipmentRow.__tablename__ == "shipments"

    def test_required_columns_present(self) -> None:
        cols = {c.name for c in ShipmentRow.__table__.columns}
        expected = {"id", "order_id", "carrier", "tracking_number", "status"}
        assert expected <= cols

    def test_id_is_primary_key(self) -> None:
        col = ShipmentRow.__table__.columns["id"]
        assert col.primary_key

    def test_order_id_is_indexed(self) -> None:
        col = ShipmentRow.__table__.columns["order_id"]
        assert col.index  # type: ignore[truthy-function]

    def test_carrier_is_not_nullable(self) -> None:
        col = ShipmentRow.__table__.columns["carrier"]
        assert not col.nullable

    def test_tracking_number_is_not_nullable(self) -> None:
        col = ShipmentRow.__table__.columns["tracking_number"]
        assert not col.nullable

    def test_status_is_not_nullable(self) -> None:
        col = ShipmentRow.__table__.columns["status"]
        assert not col.nullable


# ---------------------------------------------------------------------------
# Repository (mock-based — no real DB required)
# ---------------------------------------------------------------------------


def _make_mock_session() -> MagicMock:
    session = MagicMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.execute = AsyncMock()
    return session


def _make_session_factory(mock_session) -> Any:
    class _Ctx:
        async def __aenter__(self):
            return mock_session

        async def __aexit__(self, *_):
            pass

    return lambda: _Ctx()


def _make_shipment_row(shipment: Shipment) -> MagicMock:
    row = MagicMock()
    row.id = shipment.id
    row.order_id = shipment.order_id
    row.carrier = shipment.carrier
    row.tracking_number = shipment.tracking_number
    row.status = shipment.status.value
    return row


class TestShipmentRepository:
    """ShipmentRepository CRUD operations."""

    async def test_save_adds_row_and_commits(self) -> None:
        session = _make_mock_session()
        repo = ShipmentRepository(_make_session_factory(session))

        shipment = Shipment(
            order_id=uuid4(), carrier="DHL", tracking_number="TRK1"
        )
        await repo.save(shipment)

        session.add.assert_called_once()
        session.commit.assert_awaited_once()

    async def test_save_stores_correct_fields(self) -> None:
        session = _make_mock_session()
        repo = ShipmentRepository(_make_session_factory(session))

        oid = uuid4()
        shipment = Shipment(
            order_id=oid, carrier="UPS", tracking_number="UP9999"
        )
        await repo.save(shipment)

        added = session.add.call_args[0][0]
        assert added.order_id == oid
        assert added.carrier == "UPS"
        assert added.tracking_number == "UP9999"
        assert added.status == ShipmentStatus.PENDING.value
        assert isinstance(added, ShipmentRow)

    async def test_get_returns_shipment(self) -> None:
        shipment = Shipment(
            order_id=uuid4(), carrier="DHL", tracking_number="DHLTRK"
        )
        row = _make_shipment_row(shipment)

        session = AsyncMock()
        result = MagicMock()
        result.scalar_one.return_value = row
        session.execute.return_value = result

        repo = ShipmentRepository(_make_session_factory(session))
        fetched = await repo.get(shipment.id)

        assert fetched.id == shipment.id
        assert fetched.carrier == "DHL"
        assert fetched.tracking_number == "DHLTRK"
        assert fetched.status == ShipmentStatus.PENDING

    async def test_update_status_mutates_row_and_commits(self) -> None:
        shipment = Shipment(
            order_id=uuid4(), carrier="DHL", tracking_number="TRK"
        )
        row = _make_shipment_row(shipment)

        session = AsyncMock()
        result = MagicMock()
        result.scalar_one.return_value = row
        session.execute.return_value = result

        repo = ShipmentRepository(_make_session_factory(session))
        await repo.update_status(shipment.id, ShipmentStatus.DISPATCHED.value)

        assert row.status == ShipmentStatus.DISPATCHED.value
        session.commit.assert_awaited_once()


# ---------------------------------------------------------------------------
# Publishers
# ---------------------------------------------------------------------------


def _make_amqp_conn():
    exchange = AsyncMock()
    channel = AsyncMock()
    channel.declare_exchange.return_value = exchange

    conn = MagicMock()
    conn.channel.return_value.__aenter__ = AsyncMock(return_value=channel)
    conn.channel.return_value.__aexit__ = AsyncMock(return_value=False)
    return conn, channel, exchange


class TestShippingPublishers:
    """publish_shipment_dispatched and publish_shipment_failed."""

    async def test_publish_dispatched_routing_key(self) -> None:
        conn, channel, exchange = _make_amqp_conn()
        event = ShipmentDispatchedEvent(
            order_id=uuid4(), shipment_id=uuid4(), tracking_number="TRK1"
        )

        await publish_shipment_dispatched(event, conn)

        exchange.publish.assert_awaited_once()
        _, kwargs = exchange.publish.call_args
        assert kwargs["routing_key"] == "shipment.dispatched"

    async def test_publish_dispatched_payload_fields(self) -> None:
        conn, channel, exchange = _make_amqp_conn()
        oid, sid = uuid4(), uuid4()
        event = ShipmentDispatchedEvent(
            order_id=oid, shipment_id=sid, tracking_number="TRACK99"
        )

        await publish_shipment_dispatched(event, conn)

        raw = exchange.publish.call_args[0][0].body
        payload = json.loads(raw)
        assert payload["order_id"] == str(oid)
        assert payload["shipment_id"] == str(sid)
        assert payload["tracking_number"] == "TRACK99"
        assert "event_id" in payload
        assert "occurred_at" in payload

    async def test_publish_dispatched_declares_topic_exchange(self) -> None:
        from aio_pika import ExchangeType

        conn, channel, exchange = _make_amqp_conn()
        event = ShipmentDispatchedEvent(
            order_id=uuid4(), shipment_id=uuid4(), tracking_number="X"
        )

        await publish_shipment_dispatched(event, conn)

        channel.declare_exchange.assert_awaited_once_with(
            "events", ExchangeType.TOPIC, durable=True
        )

    async def test_publish_failed_routing_key(self) -> None:
        conn, channel, exchange = _make_amqp_conn()
        event = ShipmentFailedEvent(
            order_id=uuid4(), shipment_id=uuid4(), reason="carrier rejected"
        )

        await publish_shipment_failed(event, conn)

        _, kwargs = exchange.publish.call_args
        assert kwargs["routing_key"] == "shipment.failed"

    async def test_publish_failed_payload_fields(self) -> None:
        conn, channel, exchange = _make_amqp_conn()
        oid, sid = uuid4(), uuid4()
        event = ShipmentFailedEvent(
            order_id=oid, shipment_id=sid, reason="address not found"
        )

        await publish_shipment_failed(event, conn)

        raw = exchange.publish.call_args[0][0].body
        payload = json.loads(raw)
        assert payload["order_id"] == str(oid)
        assert payload["shipment_id"] == str(sid)
        assert payload["reason"] == "address not found"
        assert "event_id" in payload
        assert "occurred_at" in payload

    async def test_publish_failed_declares_topic_exchange(self) -> None:
        from aio_pika import ExchangeType

        conn, channel, exchange = _make_amqp_conn()
        event = ShipmentFailedEvent(
            order_id=uuid4(), shipment_id=uuid4(), reason="lost"
        )

        await publish_shipment_failed(event, conn)

        channel.declare_exchange.assert_awaited_once_with(
            "events", ExchangeType.TOPIC, durable=True
        )


# ---------------------------------------------------------------------------
# Handler
# ---------------------------------------------------------------------------


class TestHandleOrderPacked:
    """handle_order_packed saga step."""

    async def test_saves_shipment_and_publishes_dispatched(self) -> None:
        order_id = uuid4()
        event_payload = {
            "order_id": str(order_id),
            "fulfillment_id": str(uuid4()),
        }

        from unittest.mock import patch

        with (
            patch("shipping.events.handlers.ShipmentRepository") as MockRepo,
            patch(
                "shipping.events.handlers.publish_shipment_dispatched"
            ) as mock_pub,
        ):
            repo_inst = AsyncMock()
            MockRepo.return_value = repo_inst
            mock_pub.return_value = None

            await handle_order_packed(event_payload, MagicMock(), MagicMock())

        repo_inst.save.assert_awaited_once()
        mock_pub.assert_awaited_once()

    async def test_published_event_carries_order_id(self) -> None:
        order_id = uuid4()
        event_payload = {
            "order_id": str(order_id),
            "fulfillment_id": str(uuid4()),
        }

        from unittest.mock import patch

        with (
            patch("shipping.events.handlers.ShipmentRepository") as MockRepo,
            patch(
                "shipping.events.handlers.publish_shipment_dispatched"
            ) as mock_pub,
        ):
            repo_inst = AsyncMock()
            MockRepo.return_value = repo_inst
            mock_pub.return_value = None

            amqp_conn = MagicMock()
            await handle_order_packed(event_payload, MagicMock(), amqp_conn)

        published: ShipmentDispatchedEvent = mock_pub.call_args[0][0]
        assert published.order_id == order_id
        assert mock_pub.call_args[0][1] is amqp_conn

    async def test_published_shipment_id_matches_saved(self) -> None:
        order_id = uuid4()
        event_payload = {
            "order_id": str(order_id),
            "fulfillment_id": str(uuid4()),
        }

        from unittest.mock import patch

        with (
            patch("shipping.events.handlers.ShipmentRepository") as MockRepo,
            patch(
                "shipping.events.handlers.publish_shipment_dispatched"
            ) as mock_pub,
        ):
            repo_inst = AsyncMock()
            MockRepo.return_value = repo_inst
            mock_pub.return_value = None

            await handle_order_packed(event_payload, MagicMock(), MagicMock())

        saved: Shipment = repo_inst.save.call_args[0][0]
        published: ShipmentDispatchedEvent = mock_pub.call_args[0][0]
        assert published.shipment_id == saved.id

    async def test_passes_session_factory_to_repo(self) -> None:
        event_payload = {
            "order_id": str(uuid4()),
            "fulfillment_id": str(uuid4()),
        }
        sf = MagicMock()

        from unittest.mock import patch

        with (
            patch("shipping.events.handlers.ShipmentRepository") as MockRepo,
            patch("shipping.events.handlers.publish_shipment_dispatched"),
        ):
            MockRepo.return_value = AsyncMock()
            await handle_order_packed(event_payload, sf, MagicMock())

        MockRepo.assert_called_once_with(sf)

    async def test_saved_shipment_has_carrier_and_tracking(self) -> None:
        event_payload = {
            "order_id": str(uuid4()),
            "fulfillment_id": str(uuid4()),
        }

        from unittest.mock import patch

        with (
            patch("shipping.events.handlers.ShipmentRepository") as MockRepo,
            patch("shipping.events.handlers.publish_shipment_dispatched"),
        ):
            repo_inst = AsyncMock()
            MockRepo.return_value = repo_inst

            await handle_order_packed(event_payload, MagicMock(), MagicMock())

        saved: Shipment = repo_inst.save.call_args[0][0]
        assert saved.carrier
        assert saved.tracking_number


# ---------------------------------------------------------------------------
# App structure
# ---------------------------------------------------------------------------


class TestShippingApp:
    """FastAPI application wiring."""

    def test_app_title(self) -> None:
        app = create_app()
        assert app.title == "shipping-service"

    def test_app_version(self) -> None:
        app = create_app()
        assert app.version == "0.1.0"

    def test_health_route_registered(self) -> None:
        from fastapi.routing import APIRoute

        app = create_app()
        paths = {r.path for r in app.routes if isinstance(r, APIRoute)}
        assert "/health" in paths

    def test_lifespan_is_set(self) -> None:
        app = create_app()
        assert app.router.lifespan_context is not None
