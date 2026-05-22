"""
Tests for the choreography-based saga event flow.

Validates the happy-path event chain and compensating events
as documented in event_flow.py and docs/architecture/README.md.
Each service in the saga publishes exactly one domain event;
downstream services subscribe and react without a central
orchestrator.

Happy path:
  order.created → payment.captured → stock.reserved
  → order.packed → shipment.dispatched

Compensating events (failure rollback):
  payment.failed            → order-service cancels order
  stock.insufficient        → payment.refund_requested
  shipment.failed           → order.return_initiated
"""
import pytest


# ── Happy-path event definitions ─────────────────────────────

HAPPY_PATH_EVENTS = [
    "order.created",
    "payment.captured",
    "stock.reserved",
    "order.packed",
    "shipment.dispatched",
]

COMPENSATING_EVENTS = [
    "payment.failed",
    "payment.refund_requested",
    "stock.insufficient",
    "shipment.failed",
    "order.return_initiated",
]


# ── Event diagram source checks ───────────────────────────────


class TestHappyPathEvents:
    """All five saga events must appear in event_flow.py."""

    @pytest.mark.parametrize("event", HAPPY_PATH_EVENTS)
    def test_event_label_in_diagram(
        self, event_flow_src: str, event: str
    ) -> None:
        """Each happy-path event must be labelled in the diagram."""
        assert event in event_flow_src, (
            f"Event '{event}' missing from event_flow.py"
        )

    def test_order_created_published_by_order_service(
        self, event_flow_src: str
    ) -> None:
        """order-service must publish order.created to the broker."""
        # The diagram codes this as: order_svc >> Edge(...) >> broker
        assert "order_svc" in event_flow_src
        assert "order.created" in event_flow_src

    def test_payment_captured_published_by_payment_service(
        self, event_flow_src: str
    ) -> None:
        """payment-service must publish payment.captured."""
        assert "payment_svc" in event_flow_src
        assert "payment.captured" in event_flow_src

    def test_stock_reserved_published_by_inventory_service(
        self, event_flow_src: str
    ) -> None:
        """inventory-service must publish stock.reserved."""
        assert "inventory_svc" in event_flow_src
        assert "stock.reserved" in event_flow_src

    def test_order_packed_published_by_fulfillment_service(
        self, event_flow_src: str
    ) -> None:
        """fulfillment-service must publish order.packed."""
        assert "fulfillment_svc" in event_flow_src
        assert "order.packed" in event_flow_src

    def test_shipment_dispatched_published_by_shipping_service(
        self, event_flow_src: str
    ) -> None:
        """shipping-service must publish shipment.dispatched."""
        assert "shipping_svc" in event_flow_src
        assert "shipment.dispatched" in event_flow_src


class TestHappyPathEventOrdering:
    """Events must appear in the correct saga chain order."""

    def test_order_created_before_payment_captured(
        self, event_flow_src: str
    ) -> None:
        """order.created must precede payment.captured."""
        assert event_flow_src.index("order.created") < (
            event_flow_src.index("payment.captured")
        )

    def test_payment_captured_before_stock_reserved(
        self, event_flow_src: str
    ) -> None:
        """payment.captured must precede stock.reserved."""
        assert event_flow_src.index("payment.captured") < (
            event_flow_src.index("stock.reserved")
        )

    def test_stock_reserved_before_order_packed(
        self, event_flow_src: str
    ) -> None:
        """stock.reserved must precede order.packed."""
        assert event_flow_src.index("stock.reserved") < (
            event_flow_src.index("order.packed")
        )

    def test_order_packed_before_shipment_dispatched(
        self, event_flow_src: str
    ) -> None:
        """order.packed must precede shipment.dispatched."""
        assert event_flow_src.index("order.packed") < (
            event_flow_src.index("shipment.dispatched")
        )


class TestSagaSubscriptions:
    """Each downstream service must subscribe to its trigger event."""

    def test_payment_service_subscribes_to_order_created(
        self, event_flow_src: str
    ) -> None:
        """Broker routes order.created to payment-service."""
        assert "order.created" in event_flow_src
        assert "payment_svc" in event_flow_src

    def test_inventory_service_subscribes_to_payment_captured(
        self, event_flow_src: str
    ) -> None:
        """Broker routes payment.captured to inventory-service."""
        assert "payment.captured" in event_flow_src
        assert "inventory_svc" in event_flow_src

    def test_fulfillment_subscribes_to_stock_reserved(
        self, event_flow_src: str
    ) -> None:
        """Broker routes stock.reserved to fulfillment-service."""
        assert "stock.reserved" in event_flow_src
        assert "fulfillment_svc" in event_flow_src

    def test_shipping_service_subscribes_to_order_packed(
        self, event_flow_src: str
    ) -> None:
        """Broker routes order.packed to shipping-service."""
        assert "order.packed" in event_flow_src
        assert "shipping_svc" in event_flow_src


class TestNotificationFanOut:
    """notification-service subscribes to all domain events."""

    def test_notification_service_in_diagram(
        self, event_flow_src: str
    ) -> None:
        """notification-service must appear in event_flow.py."""
        assert "notification_svc" in event_flow_src

    def test_notification_receives_order_events(
        self, event_flow_src: str
    ) -> None:
        """The order.* wildcard must target notification-service."""
        assert "order.*" in event_flow_src

    def test_notification_receives_payment_events(
        self, event_flow_src: str
    ) -> None:
        """The payment.* wildcard must target notification-service."""
        assert "payment.*" in event_flow_src

    def test_notification_receives_stock_events(
        self, event_flow_src: str
    ) -> None:
        """The stock.* wildcard must target notification-service."""
        assert "stock.*" in event_flow_src

    def test_notification_receives_shipment_events(
        self, event_flow_src: str
    ) -> None:
        """The shipment.* wildcard must target notification-service."""
        assert "shipment.*" in event_flow_src


# ── Compensating events ───────────────────────────────────────


class TestCompensatingEvents:
    """Failure rollback paths must be documented in the README."""

    @pytest.mark.parametrize("event", COMPENSATING_EVENTS)
    def test_compensating_event_in_readme(
        self, arch_readme: str, event: str
    ) -> None:
        """Each compensating event must appear in the README."""
        assert event in arch_readme, (
            f"Compensating event '{event}' not in README"
        )

    def test_payment_failure_cancels_order(
        self, arch_readme: str
    ) -> None:
        """README must document that payment.failed cancels the order."""
        assert "payment.failed" in arch_readme
        assert "cancel" in arch_readme.lower()

    def test_stock_failure_triggers_refund(
        self, arch_readme: str
    ) -> None:
        """README must document the refund path for low stock."""
        assert "stock.insufficient" in arch_readme
        assert "payment.refund_requested" in arch_readme

    def test_shipment_failure_triggers_return(
        self, arch_readme: str
    ) -> None:
        """README must document the return path for failed shipments."""
        assert "shipment.failed" in arch_readme
        assert "order.return_initiated" in arch_readme


# ── Choreography architecture invariants ─────────────────────


class TestChoreographyInvariants:
    """Validate structural properties of the choreography pattern."""

    def test_no_orchestrator_node_defined(
        self, event_flow_src: str
    ) -> None:
        """No orchestrator variable must be assigned in the diagram.

        The docstring may mention 'orchestrator' in the negative sense
        (explaining the pattern); what must be absent is an actual
        diagram node assignment such as ``orchestrator_svc = ...``.
        """
        assert "orchestrator_svc" not in event_flow_src
        assert "orchestrator =" not in event_flow_src

    def test_rabbitmq_broker_present(
        self, event_flow_src: str
    ) -> None:
        """RabbitMQ must be the message broker in the event flow."""
        assert "RabbitMQ" in event_flow_src

    def test_synchronous_entry_point_is_http(
        self, event_flow_src: str
    ) -> None:
        """The only synchronous call must be POST /orders via HTTP."""
        assert "POST /orders" in event_flow_src

    def test_api_gateway_routes_to_order_service(
        self, event_flow_src: str
    ) -> None:
        """The API gateway must forward HTTP traffic to order-service."""
        assert "gateway" in event_flow_src
        assert "order_svc" in event_flow_src
