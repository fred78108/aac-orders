"""
Tests for the inventory-service bounded context.

inventory-service is step 3 of the happy-path saga: it subscribes
to payment.captured, reserves the required stock, and publishes
stock.reserved to advance the chain toward fulfillment.

If stock is unavailable it signals stock.insufficient, which
triggers payment.refund_requested from payment-service (the
compensating rollback path).

Responsibilities verified here:
  - Present in every architecture diagram
  - Assigned port :8003 and dedicated inventory_db (:5434)
  - Subscribes to payment.captured
  - Publishes stock.reserved
  - Failure condition: stock.insufficient documented
  - Domain models: StockItem and StockReservation dataclasses
  - ORM models: InventoryItemRow and ReservationRow table mappings
  - Repository: get_item, reserve, release
  - Publishers: correct routing keys and payload shape
  - Handler: saga logic for payment.captured
  - App: FastAPI app structure and health endpoint
"""

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from inventory.app import create_app
from inventory.db.models import InventoryItemRow, ReservationRow
from inventory.db.repository import StockRepository
from inventory.domain.models import StockItem, StockReservation
from inventory.events.handlers import handle_payment_captured
from inventory.events.publishers import (
    publish_stock_insufficient,
    publish_stock_reserved,
)
from shared.events import StockInsufficientEvent, StockReservedEvent


# ---------------------------------------------------------------------------
# Architecture / diagram tests (unchanged)
# ---------------------------------------------------------------------------


class TestInventoryServiceDiagramPresence:
    """inventory-service must appear in all relevant diagrams."""

    def test_in_service_overview(self, service_overview_src: str) -> None:
        """inventory-service must be in service_overview.py."""
        assert "inventory-service" in service_overview_src

    def test_in_deployment(self, deployment_src: str) -> None:
        """inventory-service must be defined in deployment.py."""
        assert "inventory-service" in deployment_src

    def test_in_event_flow(self, event_flow_src: str) -> None:
        """inventory-service must be defined in event_flow.py."""
        assert "inventory-service" in event_flow_src

    def test_service_cluster_in_service_overview(
        self, service_overview_src: str
    ) -> None:
        """A dedicated 'Inventory Service' cluster must exist."""
        assert "Inventory Service" in service_overview_src


class TestInventoryServicePorts:
    """inventory-service must use the correct assigned ports."""

    def test_service_port_8003(self, deployment_src: str) -> None:
        """inventory-service must be assigned port 8003."""
        assert ":8003" in deployment_src

    def test_database_container_name(self, deployment_src: str) -> None:
        """The paired DB container must be postgres-inventory."""
        assert "postgres-inventory" in deployment_src

    def test_database_port_5434(self, deployment_src: str) -> None:
        """inventory_db must be on port 5434."""
        assert ":5434" in deployment_src

    def test_database_name_in_service_overview(
        self, service_overview_src: str
    ) -> None:
        """inventory_db must appear paired with inventory-service."""
        assert "inventory_db" in service_overview_src


class TestInventoryServiceEvents:
    """inventory-service event subscription and publishing rules."""

    def test_subscribes_to_payment_captured(self, event_flow_src: str) -> None:
        """inventory-service must subscribe to payment.captured."""
        assert "payment.captured" in event_flow_src
        assert "inventory_svc" in event_flow_src

    def test_publishes_stock_reserved(self, event_flow_src: str) -> None:
        """inventory-service must publish stock.reserved."""
        assert "stock.reserved" in event_flow_src

    def test_stock_reserved_follows_payment_captured(
        self, event_flow_src: str
    ) -> None:
        """stock.reserved must appear after payment.captured."""
        assert event_flow_src.index("payment.captured") < (
            event_flow_src.index("stock.reserved")
        )

    def test_stock_reserved_precedes_order_packed(
        self, event_flow_src: str
    ) -> None:
        """stock.reserved must appear before order.packed."""
        assert event_flow_src.index("stock.reserved") < (
            event_flow_src.index("order.packed")
        )


class TestInventoryServiceCompensation:
    """inventory-service failure condition must be documented."""

    def test_stock_insufficient_in_readme(self, arch_readme: str) -> None:
        """stock.insufficient must appear in the README."""
        assert "stock.insufficient" in arch_readme

    def test_stock_insufficient_triggers_refund(
        self, arch_readme: str
    ) -> None:
        """README must link stock.insufficient to a refund request."""
        assert "stock.insufficient" in arch_readme
        assert "payment.refund_requested" in arch_readme


# ---------------------------------------------------------------------------
# Domain model
# ---------------------------------------------------------------------------


class TestStockItemDomainModel:
    """StockItem dataclass behaviour."""

    def test_id_is_auto_generated(self) -> None:
        i1 = StockItem(sku="SKU-A", quantity_available=10)
        i2 = StockItem(sku="SKU-B", quantity_available=5)
        assert i1.id != i2.id

    def test_fields_set_correctly(self) -> None:
        item = StockItem(sku="WIDGET-1", quantity_available=42)
        assert item.sku == "WIDGET-1"
        assert item.quantity_available == 42


class TestStockReservationDomainModel:
    """StockReservation dataclass behaviour."""

    def test_id_is_auto_generated(self) -> None:
        r1 = StockReservation(order_id=uuid4(), items=[])
        r2 = StockReservation(order_id=uuid4(), items=[])
        assert r1.id != r2.id

    def test_holds_items(self) -> None:
        items = [
            StockItem(sku="A", quantity_available=1),
            StockItem(sku="B", quantity_available=2),
        ]
        reservation = StockReservation(order_id=uuid4(), items=items)
        assert len(reservation.items) == 2
        assert reservation.items[0].sku == "A"


# ---------------------------------------------------------------------------
# ORM models
# ---------------------------------------------------------------------------


class TestInventoryItemRowORM:
    """InventoryItemRow SQLAlchemy mapping."""

    def test_tablename(self) -> None:
        assert InventoryItemRow.__tablename__ == "inventory_items"

    def test_required_columns_present(self) -> None:
        cols = {c.name for c in InventoryItemRow.__table__.columns}
        assert {"id", "sku", "quantity_available"} <= cols

    def test_id_is_primary_key(self) -> None:
        col = InventoryItemRow.__table__.columns["id"]
        assert col.primary_key

    def test_sku_is_indexed(self) -> None:
        col = InventoryItemRow.__table__.columns["sku"]
        assert col.index  # type: ignore[truthy-function]

    def test_sku_is_unique(self) -> None:
        col = InventoryItemRow.__table__.columns["sku"]
        assert col.unique  # type: ignore[truthy-function]

    def test_quantity_available_is_not_nullable(self) -> None:
        col = InventoryItemRow.__table__.columns["quantity_available"]
        assert not col.nullable


class TestReservationRowORM:
    """ReservationRow SQLAlchemy mapping."""

    def test_tablename(self) -> None:
        assert ReservationRow.__tablename__ == "reservations"

    def test_required_columns_present(self) -> None:
        cols = {c.name for c in ReservationRow.__table__.columns}
        assert {
            "id",
            "reservation_id",
            "order_id",
            "sku",
            "quantity_reserved",
        } <= cols

    def test_id_is_primary_key(self) -> None:
        col = ReservationRow.__table__.columns["id"]
        assert col.primary_key

    def test_reservation_id_is_indexed(self) -> None:
        col = ReservationRow.__table__.columns["reservation_id"]
        assert col.index  # type: ignore[truthy-function]

    def test_order_id_is_indexed(self) -> None:
        col = ReservationRow.__table__.columns["order_id"]
        assert col.index  # type: ignore[truthy-function]

    def test_quantity_reserved_is_not_nullable(self) -> None:
        col = ReservationRow.__table__.columns["quantity_reserved"]
        assert not col.nullable


# ---------------------------------------------------------------------------
# Repository (mock-based — no real DB required)
# ---------------------------------------------------------------------------


def _make_mock_session() -> MagicMock:
    session = MagicMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.execute = AsyncMock()
    session.delete = AsyncMock()
    return session


def _make_session_factory(mock_session) -> Any:
    class _Ctx:
        async def __aenter__(self):
            return mock_session

        async def __aexit__(self, *_):
            pass

    return lambda: _Ctx()


def _make_item_row(item: StockItem) -> MagicMock:
    row = MagicMock()
    row.id = item.id
    row.sku = item.sku
    row.quantity_available = item.quantity_available
    return row


class TestStockRepository:
    """StockRepository CRUD operations."""

    async def test_get_item_returns_stock_item(self) -> None:
        item = StockItem(sku="WIDGET-1", quantity_available=20)
        row = _make_item_row(item)

        session = AsyncMock()
        result = MagicMock()
        result.scalar_one.return_value = row
        session.execute.return_value = result

        repo = StockRepository(_make_session_factory(session))
        fetched = await repo.get_item("WIDGET-1")

        assert fetched.sku == "WIDGET-1"
        assert fetched.quantity_available == 20

    async def test_reserve_adds_row_per_item_and_commits(self) -> None:
        session = _make_mock_session()
        repo = StockRepository(_make_session_factory(session))

        reservation = StockReservation(
            order_id=uuid4(),
            items=[
                StockItem(sku="A", quantity_available=1),
                StockItem(sku="B", quantity_available=3),
            ],
        )
        await repo.reserve(reservation)

        assert session.add.call_count == 2
        session.commit.assert_awaited_once()

    async def test_reserve_stores_correct_sku_and_quantity(self) -> None:
        session = _make_mock_session()
        repo = StockRepository(_make_session_factory(session))

        item = StockItem(sku="WIDGET-X", quantity_available=5)
        reservation = StockReservation(order_id=uuid4(), items=[item])
        await repo.reserve(reservation)

        added: ReservationRow = session.add.call_args[0][0]
        assert isinstance(added, ReservationRow)
        assert added.sku == "WIDGET-X"
        assert added.quantity_reserved == 5

    async def test_reserve_links_reservation_id_and_order_id(self) -> None:
        session = _make_mock_session()
        repo = StockRepository(_make_session_factory(session))

        order_id = uuid4()
        reservation = StockReservation(
            order_id=order_id,
            items=[StockItem(sku="X", quantity_available=1)],
        )
        await repo.reserve(reservation)

        added: ReservationRow = session.add.call_args[0][0]
        assert added.reservation_id == reservation.id
        assert added.order_id == order_id

    async def test_release_deletes_rows_and_commits(self) -> None:
        row1, row2 = MagicMock(), MagicMock()

        session = AsyncMock()
        result = MagicMock()
        result.scalars.return_value.all.return_value = [row1, row2]
        session.execute.return_value = result

        repo = StockRepository(_make_session_factory(session))
        await repo.release(uuid4())

        assert session.delete.await_count == 2
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


class TestInventoryPublishers:
    """publish_stock_reserved and publish_stock_insufficient."""

    async def test_publish_reserved_uses_correct_routing_key(self) -> None:
        conn, channel, exchange = _make_amqp_conn()
        event = StockReservedEvent(order_id=uuid4(), reservation_id=uuid4())

        await publish_stock_reserved(event, conn)

        exchange.publish.assert_awaited_once()
        _, kwargs = exchange.publish.call_args
        assert kwargs["routing_key"] == "stock.reserved"

    async def test_publish_reserved_payload_fields(self) -> None:
        conn, channel, exchange = _make_amqp_conn()
        oid, rid = uuid4(), uuid4()
        event = StockReservedEvent(order_id=oid, reservation_id=rid)

        await publish_stock_reserved(event, conn)

        raw = exchange.publish.call_args[0][0].body
        payload = json.loads(raw)
        assert payload["order_id"] == str(oid)
        assert payload["reservation_id"] == str(rid)
        assert "event_id" in payload
        assert "occurred_at" in payload

    async def test_publish_reserved_declares_topic_exchange(self) -> None:
        from aio_pika import ExchangeType

        conn, channel, exchange = _make_amqp_conn()
        event = StockReservedEvent(order_id=uuid4(), reservation_id=uuid4())

        await publish_stock_reserved(event, conn)

        channel.declare_exchange.assert_awaited_once_with(
            "events", ExchangeType.TOPIC, durable=True
        )

    async def test_publish_insufficient_uses_correct_routing_key(
        self,
    ) -> None:
        conn, channel, exchange = _make_amqp_conn()
        event = StockInsufficientEvent(order_id=uuid4(), sku="WIDGET-1")

        await publish_stock_insufficient(event, conn)

        _, kwargs = exchange.publish.call_args
        assert kwargs["routing_key"] == "stock.insufficient"

    async def test_publish_insufficient_payload_fields(self) -> None:
        conn, channel, exchange = _make_amqp_conn()
        oid = uuid4()
        event = StockInsufficientEvent(order_id=oid, sku="GADGET-7")

        await publish_stock_insufficient(event, conn)

        raw = exchange.publish.call_args[0][0].body
        payload = json.loads(raw)
        assert payload["order_id"] == str(oid)
        assert payload["sku"] == "GADGET-7"
        assert "event_id" in payload
        assert "occurred_at" in payload

    async def test_publish_insufficient_declares_topic_exchange(self) -> None:
        from aio_pika import ExchangeType

        conn, channel, exchange = _make_amqp_conn()
        event = StockInsufficientEvent(order_id=uuid4(), sku="X")

        await publish_stock_insufficient(event, conn)

        channel.declare_exchange.assert_awaited_once_with(
            "events", ExchangeType.TOPIC, durable=True
        )


# ---------------------------------------------------------------------------
# Handler
# ---------------------------------------------------------------------------


class TestHandlePaymentCaptured:
    """handle_payment_captured saga step."""

    async def test_reserves_stock_and_publishes_reserved(self) -> None:
        order_id = uuid4()
        event_payload = {
            "order_id": str(order_id),
            "payment_id": str(uuid4()),
            "amount_cents": 1500,
        }

        with (
            patch("inventory.events.handlers.StockRepository") as MockRepo,
            patch(
                "inventory.events.handlers.publish_stock_reserved"
            ) as mock_pub,
        ):
            repo_inst = AsyncMock()
            MockRepo.return_value = repo_inst
            mock_pub.return_value = None

            await handle_payment_captured(
                event_payload, MagicMock(), MagicMock()
            )

        repo_inst.reserve.assert_awaited_once()
        mock_pub.assert_awaited_once()

    async def test_publishes_with_correct_order_id(self) -> None:
        order_id = uuid4()
        event_payload = {
            "order_id": str(order_id),
            "payment_id": str(uuid4()),
            "amount_cents": 800,
        }

        with (
            patch("inventory.events.handlers.StockRepository") as MockRepo,
            patch(
                "inventory.events.handlers.publish_stock_reserved"
            ) as mock_pub,
        ):
            repo_inst = AsyncMock()
            MockRepo.return_value = repo_inst
            mock_pub.return_value = None

            amqp_conn = MagicMock()
            await handle_payment_captured(
                event_payload, MagicMock(), amqp_conn
            )

        published: StockReservedEvent = mock_pub.call_args[0][0]
        assert published.order_id == order_id
        assert mock_pub.call_args[0][1] is amqp_conn

    async def test_reservation_carries_order_id(self) -> None:
        order_id = uuid4()
        event_payload = {
            "order_id": str(order_id),
            "payment_id": str(uuid4()),
            "amount_cents": 200,
        }

        with (
            patch("inventory.events.handlers.StockRepository") as MockRepo,
            patch("inventory.events.handlers.publish_stock_reserved"),
        ):
            repo_inst = AsyncMock()
            MockRepo.return_value = repo_inst

            await handle_payment_captured(
                event_payload, MagicMock(), MagicMock()
            )

        reserved: StockReservation = repo_inst.reserve.call_args[0][0]
        assert reserved.order_id == order_id

    async def test_passes_session_factory_to_repo(self) -> None:
        event_payload = {
            "order_id": str(uuid4()),
            "payment_id": str(uuid4()),
            "amount_cents": 100,
        }
        sf = MagicMock()

        with (
            patch("inventory.events.handlers.StockRepository") as MockRepo,
            patch("inventory.events.handlers.publish_stock_reserved"),
        ):
            MockRepo.return_value = AsyncMock()
            await handle_payment_captured(event_payload, sf, MagicMock())

        MockRepo.assert_called_once_with(sf)

    async def test_published_reservation_id_matches_reserved(self) -> None:
        order_id = uuid4()
        event_payload = {
            "order_id": str(order_id),
            "payment_id": str(uuid4()),
            "amount_cents": 500,
        }

        with (
            patch("inventory.events.handlers.StockRepository") as MockRepo,
            patch(
                "inventory.events.handlers.publish_stock_reserved"
            ) as mock_pub,
        ):
            repo_inst = AsyncMock()
            MockRepo.return_value = repo_inst
            mock_pub.return_value = None

            await handle_payment_captured(
                event_payload, MagicMock(), MagicMock()
            )

        reserved: StockReservation = repo_inst.reserve.call_args[0][0]
        published: StockReservedEvent = mock_pub.call_args[0][0]
        assert published.reservation_id == reserved.id


# ---------------------------------------------------------------------------
# App structure
# ---------------------------------------------------------------------------


class TestInventoryApp:
    """FastAPI application wiring."""

    def test_app_title(self) -> None:
        app = create_app()
        assert app.title == "inventory-service"

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
