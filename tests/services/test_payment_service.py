"""
Tests for the payment-service bounded context.

payment-service is step 2 of the happy-path saga: it subscribes
to order.created, charges the customer via an external gateway,
then publishes payment.captured to advance the chain.

On failure it emits payment.refund_requested (triggered by
stock.insufficient from inventory-service) so the upstream
payment can be reversed.

Responsibilities verified here:
  - Present in every architecture diagram
  - Assigned port :8002 and dedicated payments_db (:5433)
  - Subscribes to order.created
  - Publishes payment.captured
  - Compensating event: payment.refund_requested documented
  - Domain model: Payment dataclass and PaymentStatus enum
  - ORM model: PaymentRow table mapping
  - Repository: save, get, get_by_order_id, update_status
  - Publishers: correct routing keys and payload shape
  - Handlers: saga logic for order.created and stock.insufficient
  - App: FastAPI app structure and health endpoint
"""
import json
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from payment.app import create_app
from payment.db.models import PaymentRow
from payment.db.repository import PaymentRepository
from payment.domain.models import Payment, PaymentStatus
from payment.events.handlers import handle_order_created, handle_stock_insufficient
from payment.events.publishers import (
    publish_payment_captured,
    publish_payment_refund_requested,
)
from shared.events import PaymentCapturedEvent, PaymentRefundRequestedEvent


# ---------------------------------------------------------------------------
# Architecture / diagram tests (unchanged)
# ---------------------------------------------------------------------------


class TestPaymentServiceDiagramPresence:
    """payment-service must appear in all relevant diagrams."""

    def test_in_service_overview(
        self, service_overview_src: str
    ) -> None:
        """payment-service must be defined in service_overview.py."""
        assert "payment-service" in service_overview_src

    def test_in_deployment(self, deployment_src: str) -> None:
        """payment-service must be defined in deployment.py."""
        assert "payment-service" in deployment_src

    def test_in_event_flow(self, event_flow_src: str) -> None:
        """payment-service must be defined in event_flow.py."""
        assert "payment-service" in event_flow_src

    def test_service_cluster_in_service_overview(
        self, service_overview_src: str
    ) -> None:
        """A dedicated 'Payment Service' cluster must exist."""
        assert "Payment Service" in service_overview_src


class TestPaymentServicePorts:
    """payment-service must use the correct assigned ports."""

    def test_service_port_8002(self, deployment_src: str) -> None:
        """payment-service must be assigned port 8002."""
        assert ":8002" in deployment_src

    def test_database_container_name(
        self, deployment_src: str
    ) -> None:
        """The paired DB container must be postgres-payments."""
        assert "postgres-payments" in deployment_src

    def test_database_port_5433(
        self, deployment_src: str
    ) -> None:
        """payments_db must be on port 5433."""
        assert ":5433" in deployment_src

    def test_database_name_in_service_overview(
        self, service_overview_src: str
    ) -> None:
        """payments_db must appear paired with payment-service."""
        assert "payments_db" in service_overview_src


class TestPaymentServiceEvents:
    """payment-service event subscription and publishing rules."""

    def test_subscribes_to_order_created(
        self, event_flow_src: str
    ) -> None:
        """payment-service must subscribe to order.created."""
        assert "order.created" in event_flow_src
        assert "payment_svc" in event_flow_src

    def test_publishes_payment_captured(
        self, event_flow_src: str
    ) -> None:
        """payment-service must publish payment.captured."""
        assert "payment.captured" in event_flow_src

    def test_payment_captured_follows_order_created(
        self, event_flow_src: str
    ) -> None:
        """payment.captured must appear after order.created."""
        assert event_flow_src.index("order.created") < (
            event_flow_src.index("payment.captured")
        )

    def test_payment_captured_precedes_stock_reserved(
        self, event_flow_src: str
    ) -> None:
        """payment.captured must appear before stock.reserved."""
        assert event_flow_src.index("payment.captured") < (
            event_flow_src.index("stock.reserved")
        )


class TestPaymentServiceCompensation:
    """payment-service must handle the refund compensation path."""

    def test_payment_refund_requested_in_readme(
        self, arch_readme: str
    ) -> None:
        """payment.refund_requested must appear in the README."""
        assert "payment.refund_requested" in arch_readme

    def test_stock_insufficient_triggers_refund(
        self, arch_readme: str
    ) -> None:
        """README must link stock.insufficient to the refund path."""
        assert "stock.insufficient" in arch_readme
        assert "payment.refund_requested" in arch_readme

    def test_payment_service_named_as_refund_handler(
        self, arch_readme: str
    ) -> None:
        """README must name payment-service as the refund handler."""
        assert "payment-service" in arch_readme


# ---------------------------------------------------------------------------
# Domain model
# ---------------------------------------------------------------------------


class TestPaymentDomainModel:
    """Payment dataclass and PaymentStatus enum behaviour."""

    def test_default_status_is_pending(self) -> None:
        p = Payment(order_id=uuid4(), customer_id=uuid4(), amount_cents=500)
        assert p.status is PaymentStatus.PENDING

    def test_id_is_auto_generated(self) -> None:
        p1 = Payment(order_id=uuid4(), customer_id=uuid4(), amount_cents=100)
        p2 = Payment(order_id=uuid4(), customer_id=uuid4(), amount_cents=100)
        assert p1.id != p2.id

    def test_status_can_be_overridden(self) -> None:
        p = Payment(
            order_id=uuid4(),
            customer_id=uuid4(),
            amount_cents=100,
            status=PaymentStatus.CAPTURED,
        )
        assert p.status is PaymentStatus.CAPTURED

    def test_all_status_values_are_strings(self) -> None:
        for s in PaymentStatus:
            assert isinstance(s.value, str)

    def test_status_enum_members(self) -> None:
        members = {s.value for s in PaymentStatus}
        assert members == {"pending", "captured", "failed", "refunded"}


# ---------------------------------------------------------------------------
# ORM model
# ---------------------------------------------------------------------------


class TestPaymentRowORM:
    """PaymentRow SQLAlchemy mapping."""

    def test_tablename(self) -> None:
        assert PaymentRow.__tablename__ == "payments"

    def test_required_columns_present(self) -> None:
        cols = {c.name for c in PaymentRow.__table__.columns}
        assert {"id", "order_id", "customer_id", "amount_cents", "status"} <= cols

    def test_order_id_is_indexed(self) -> None:
        col = PaymentRow.__table__.columns["order_id"]
        assert col.index

    def test_id_is_primary_key(self) -> None:
        col = PaymentRow.__table__.columns["id"]
        assert col.primary_key

    def test_status_is_not_nullable(self) -> None:
        col = PaymentRow.__table__.columns["status"]
        assert not col.nullable

    def test_amount_cents_is_not_nullable(self) -> None:
        col = PaymentRow.__table__.columns["amount_cents"]
        assert not col.nullable


# ---------------------------------------------------------------------------
# Repository (mock-based — no real DB required)
# ---------------------------------------------------------------------------


def _make_mock_session() -> MagicMock:
    """Return a mock session with sync add() and async execute/commit."""
    session = MagicMock()
    session.add = MagicMock()  # synchronous on real SQLAlchemy sessions
    session.commit = AsyncMock()
    session.execute = AsyncMock()
    return session


def _make_session_factory(mock_session):
    """Return a callable session factory that yields mock_session."""

    class _Ctx:
        async def __aenter__(self):
            return mock_session

        async def __aexit__(self, *_):
            pass

    return lambda: _Ctx()


def _make_payment_row(payment: Payment) -> MagicMock:
    row = MagicMock()
    row.id = payment.id
    row.order_id = payment.order_id
    row.customer_id = payment.customer_id
    row.amount_cents = payment.amount_cents
    row.status = payment.status.value
    return row


class TestPaymentRepository:
    """PaymentRepository CRUD operations."""

    async def test_save_adds_row_and_commits(self) -> None:
        session = _make_mock_session()
        repo = PaymentRepository(_make_session_factory(session))
        payment = Payment(order_id=uuid4(), customer_id=uuid4(), amount_cents=999)

        await repo.save(payment)

        session.add.assert_called_once()
        added = session.add.call_args[0][0]
        assert isinstance(added, PaymentRow)
        assert added.amount_cents == 999
        session.commit.assert_awaited_once()

    async def test_save_persists_correct_status(self) -> None:
        session = _make_mock_session()
        repo = PaymentRepository(_make_session_factory(session))
        payment = Payment(
            order_id=uuid4(),
            customer_id=uuid4(),
            amount_cents=200,
            status=PaymentStatus.CAPTURED,
        )

        await repo.save(payment)

        added = session.add.call_args[0][0]
        assert added.status == "captured"

    async def test_get_returns_domain_payment(self) -> None:
        payment = Payment(order_id=uuid4(), customer_id=uuid4(), amount_cents=300)
        row = _make_payment_row(payment)

        session = AsyncMock()
        result = MagicMock()
        result.scalar_one.return_value = row
        session.execute.return_value = result

        repo = PaymentRepository(_make_session_factory(session))
        fetched = await repo.get(payment.id)

        assert fetched.id == payment.id
        assert fetched.amount_cents == 300
        assert fetched.status is PaymentStatus.PENDING

    async def test_get_by_order_id_returns_correct_payment(self) -> None:
        payment = Payment(order_id=uuid4(), customer_id=uuid4(), amount_cents=450)
        row = _make_payment_row(payment)

        session = AsyncMock()
        result = MagicMock()
        result.scalar_one.return_value = row
        session.execute.return_value = result

        repo = PaymentRepository(_make_session_factory(session))
        fetched = await repo.get_by_order_id(payment.order_id)

        assert fetched.order_id == payment.order_id
        assert fetched.amount_cents == 450

    async def test_update_status_mutates_row_and_commits(self) -> None:
        payment = Payment(order_id=uuid4(), customer_id=uuid4(), amount_cents=100)
        row = _make_payment_row(payment)

        session = AsyncMock()
        result = MagicMock()
        result.scalar_one.return_value = row
        session.execute.return_value = result

        repo = PaymentRepository(_make_session_factory(session))
        await repo.update_status(payment.id, "captured")

        assert row.status == "captured"
        session.commit.assert_awaited_once()


# ---------------------------------------------------------------------------
# Publishers
# ---------------------------------------------------------------------------


def _make_amqp_conn():
    """Return a mock aio_pika connection with a usable channel context."""
    exchange = AsyncMock()
    channel = AsyncMock()
    channel.declare_exchange.return_value = exchange

    conn = MagicMock()
    conn.channel.return_value.__aenter__ = AsyncMock(return_value=channel)
    conn.channel.return_value.__aexit__ = AsyncMock(return_value=False)
    return conn, channel, exchange


class TestPaymentPublishers:
    """publish_payment_captured and publish_payment_refund_requested."""

    async def test_publish_captured_uses_correct_routing_key(self) -> None:
        conn, channel, exchange = _make_amqp_conn()
        event = PaymentCapturedEvent(
            order_id=uuid4(), payment_id=uuid4(), amount_cents=1000
        )

        await publish_payment_captured(event, conn)

        exchange.publish.assert_awaited_once()
        _, kwargs = exchange.publish.call_args
        assert kwargs["routing_key"] == "payment.captured"

    async def test_publish_captured_payload_fields(self) -> None:
        conn, channel, exchange = _make_amqp_conn()
        oid, pid = uuid4(), uuid4()
        event = PaymentCapturedEvent(order_id=oid, payment_id=pid, amount_cents=750)

        await publish_payment_captured(event, conn)

        raw = exchange.publish.call_args[0][0].body
        payload = json.loads(raw)
        assert payload["order_id"] == str(oid)
        assert payload["payment_id"] == str(pid)
        assert payload["amount_cents"] == 750
        assert "event_id" in payload
        assert "occurred_at" in payload

    async def test_publish_captured_declares_topic_exchange(self) -> None:
        from aio_pika import ExchangeType

        conn, channel, exchange = _make_amqp_conn()
        event = PaymentCapturedEvent(
            order_id=uuid4(), payment_id=uuid4(), amount_cents=100
        )

        await publish_payment_captured(event, conn)

        channel.declare_exchange.assert_awaited_once_with(
            "events", ExchangeType.TOPIC, durable=True
        )

    async def test_publish_refund_requested_routing_key(self) -> None:
        conn, channel, exchange = _make_amqp_conn()
        event = PaymentRefundRequestedEvent(
            order_id=uuid4(), payment_id=uuid4(), amount_cents=500
        )

        await publish_payment_refund_requested(event, conn)

        _, kwargs = exchange.publish.call_args
        assert kwargs["routing_key"] == "payment.refund_requested"

    async def test_publish_refund_requested_payload_fields(self) -> None:
        conn, channel, exchange = _make_amqp_conn()
        oid, pid = uuid4(), uuid4()
        event = PaymentRefundRequestedEvent(
            order_id=oid, payment_id=pid, amount_cents=250
        )

        await publish_payment_refund_requested(event, conn)

        raw = exchange.publish.call_args[0][0].body
        payload = json.loads(raw)
        assert payload["order_id"] == str(oid)
        assert payload["payment_id"] == str(pid)
        assert payload["amount_cents"] == 250

    async def test_publish_refund_declares_topic_exchange(self) -> None:
        from aio_pika import ExchangeType

        conn, channel, exchange = _make_amqp_conn()
        event = PaymentRefundRequestedEvent(
            order_id=uuid4(), payment_id=uuid4(), amount_cents=100
        )

        await publish_payment_refund_requested(event, conn)

        channel.declare_exchange.assert_awaited_once_with(
            "events", ExchangeType.TOPIC, durable=True
        )


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------


class TestHandleOrderCreated:
    """handle_order_created saga step."""

    async def test_saves_payment_and_publishes_captured(self) -> None:
        order_id, customer_id = uuid4(), uuid4()
        event_payload = {
            "order_id": str(order_id),
            "customer_id": str(customer_id),
            "total_cents": 1500,
        }

        with (
            patch("payment.events.handlers.PaymentRepository") as MockRepo,
            patch("payment.events.handlers.publish_payment_captured") as mock_pub,
        ):
            repo_inst = AsyncMock()
            MockRepo.return_value = repo_inst
            mock_pub.return_value = None

            session_factory = MagicMock()
            amqp_conn = MagicMock()

            await handle_order_created(event_payload, session_factory, amqp_conn)

        repo_inst.save.assert_awaited_once()
        saved: Payment = repo_inst.save.call_args[0][0]
        assert saved.order_id == order_id
        assert saved.customer_id == customer_id
        assert saved.amount_cents == 1500

    async def test_updates_status_to_captured(self) -> None:
        order_id, customer_id = uuid4(), uuid4()
        event_payload = {
            "order_id": str(order_id),
            "customer_id": str(customer_id),
            "total_cents": 800,
        }

        with (
            patch("payment.events.handlers.PaymentRepository") as MockRepo,
            patch("payment.events.handlers.publish_payment_captured"),
        ):
            repo_inst = AsyncMock()
            MockRepo.return_value = repo_inst

            await handle_order_created(event_payload, MagicMock(), MagicMock())

        repo_inst.update_status.assert_awaited_once()
        _, status_arg = repo_inst.update_status.call_args[0]
        assert status_arg == "captured"

    async def test_publishes_captured_event_with_correct_fields(self) -> None:
        order_id, customer_id = uuid4(), uuid4()
        event_payload = {
            "order_id": str(order_id),
            "customer_id": str(customer_id),
            "total_cents": 600,
        }

        with (
            patch("payment.events.handlers.PaymentRepository") as MockRepo,
            patch("payment.events.handlers.publish_payment_captured") as mock_pub,
        ):
            repo_inst = AsyncMock()
            MockRepo.return_value = repo_inst
            mock_pub.return_value = None

            amqp_conn = MagicMock()
            await handle_order_created(event_payload, MagicMock(), amqp_conn)

        published: PaymentCapturedEvent = mock_pub.call_args[0][0]
        assert published.order_id == order_id
        assert published.amount_cents == 600
        assert mock_pub.call_args[0][1] is amqp_conn

    async def test_passes_session_factory_to_repo(self) -> None:
        event_payload = {
            "order_id": str(uuid4()),
            "customer_id": str(uuid4()),
            "total_cents": 100,
        }
        sf = MagicMock()

        with (
            patch("payment.events.handlers.PaymentRepository") as MockRepo,
            patch("payment.events.handlers.publish_payment_captured"),
        ):
            MockRepo.return_value = AsyncMock()
            await handle_order_created(event_payload, sf, MagicMock())

        MockRepo.assert_called_once_with(sf)


class TestHandleStockInsufficient:
    """handle_stock_insufficient compensation step."""

    async def test_looks_up_payment_by_order_id(self) -> None:
        order_id = uuid4()
        event_payload = {"order_id": str(order_id), "sku": "WIDGET-1"}
        existing = Payment(order_id=order_id, customer_id=uuid4(), amount_cents=400)

        with (
            patch("payment.events.handlers.PaymentRepository") as MockRepo,
            patch("payment.events.handlers.publish_payment_refund_requested"),
        ):
            repo_inst = AsyncMock()
            repo_inst.get_by_order_id.return_value = existing
            MockRepo.return_value = repo_inst

            await handle_stock_insufficient(event_payload, MagicMock(), MagicMock())

        repo_inst.get_by_order_id.assert_awaited_once_with(order_id)

    async def test_updates_status_to_refunded(self) -> None:
        order_id = uuid4()
        event_payload = {"order_id": str(order_id), "sku": "WIDGET-1"}
        existing = Payment(order_id=order_id, customer_id=uuid4(), amount_cents=400)

        with (
            patch("payment.events.handlers.PaymentRepository") as MockRepo,
            patch("payment.events.handlers.publish_payment_refund_requested"),
        ):
            repo_inst = AsyncMock()
            repo_inst.get_by_order_id.return_value = existing
            MockRepo.return_value = repo_inst

            await handle_stock_insufficient(event_payload, MagicMock(), MagicMock())

        repo_inst.update_status.assert_awaited_once_with(existing.id, "refunded")

    async def test_publishes_refund_event_with_correct_fields(self) -> None:
        order_id = uuid4()
        event_payload = {"order_id": str(order_id), "sku": "WIDGET-1"}
        existing = Payment(order_id=order_id, customer_id=uuid4(), amount_cents=700)

        with (
            patch("payment.events.handlers.PaymentRepository") as MockRepo,
            patch(
                "payment.events.handlers.publish_payment_refund_requested"
            ) as mock_pub,
        ):
            repo_inst = AsyncMock()
            repo_inst.get_by_order_id.return_value = existing
            MockRepo.return_value = repo_inst
            mock_pub.return_value = None

            amqp_conn = MagicMock()
            await handle_stock_insufficient(event_payload, MagicMock(), amqp_conn)

        published: PaymentRefundRequestedEvent = mock_pub.call_args[0][0]
        assert published.order_id == order_id
        assert published.payment_id == existing.id
        assert published.amount_cents == 700
        assert mock_pub.call_args[0][1] is amqp_conn


# ---------------------------------------------------------------------------
# App structure
# ---------------------------------------------------------------------------


class TestPaymentApp:
    """FastAPI application wiring."""

    def test_app_title(self) -> None:
        app = create_app()
        assert app.title == "payment-service"

    def test_app_version(self) -> None:
        app = create_app()
        assert app.version == "0.1.0"

    def test_health_route_registered(self) -> None:
        app = create_app()
        paths = {r.path for r in app.routes}
        assert "/health" in paths

    def test_lifespan_is_set(self) -> None:
        app = create_app()
        assert app.router.lifespan_context is not None
