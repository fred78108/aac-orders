"""
Tests for the order-service bounded context.

order-service is the saga entry point: it receives the single
synchronous HTTP call (POST /orders via the API gateway) and
publishes order.created to kick off the choreography chain.

Responsibilities verified here:
  - Present in every architecture diagram
  - Assigned port :8001 and dedicated orders_db (:5432)
  - Publishes order.created (step 1 of the happy path)
  - Is the sole synchronous HTTP receiver
  - Compensating path: handles payment.failed by cancelling
    the order (documented in the architecture README)
"""


class TestOrderServiceDiagramPresence:
    """order-service must appear in all relevant diagrams."""

    def test_in_service_overview(self, service_overview_src: str) -> None:
        """order-service must be defined in service_overview.py."""
        assert "order-service" in service_overview_src

    def test_in_deployment(self, deployment_src: str) -> None:
        """order-service must be defined in deployment.py."""
        assert "order-service" in deployment_src

    def test_in_event_flow(self, event_flow_src: str) -> None:
        """order-service must be defined in event_flow.py."""
        assert "order-service" in event_flow_src

    def test_service_cluster_in_service_overview(
        self, service_overview_src: str
    ) -> None:
        """A dedicated 'Order Service' cluster must exist."""
        assert "Order Service" in service_overview_src


class TestOrderServicePorts:
    """order-service must use the correct assigned ports."""

    def test_service_port_8001(self, deployment_src: str) -> None:
        """order-service must be assigned port 8001."""
        assert ":8001" in deployment_src

    def test_database_container_name(self, deployment_src: str) -> None:
        """The paired DB container must be postgres-orders."""
        assert "postgres-orders" in deployment_src

    def test_database_port_5432(self, deployment_src: str) -> None:
        """orders_db must be on the base Postgres port 5432."""
        assert ":5432" in deployment_src

    def test_database_name_in_service_overview(
        self, service_overview_src: str
    ) -> None:
        """orders_db must appear paired with order-service."""
        assert "orders_db" in service_overview_src


class TestOrderServiceEvents:
    """order-service event publishing and subscription rules."""

    def test_publishes_order_created(self, event_flow_src: str) -> None:
        """order-service must publish the order.created event."""
        assert "order.created" in event_flow_src

    def test_is_http_entry_point(self, event_flow_src: str) -> None:
        """order-service must receive the POST /orders HTTP call."""
        assert "POST /orders" in event_flow_src

    def test_gateway_routes_to_order_service(
        self, event_flow_src: str
    ) -> None:
        """The API gateway must forward HTTP traffic to order-service."""
        assert "gateway" in event_flow_src
        assert "order_svc" in event_flow_src

    def test_order_created_is_first_saga_event(
        self, event_flow_src: str
    ) -> None:
        """order.created must appear before all other saga events."""
        pos = event_flow_src.index("order.created")
        for later_event in [
            "payment.captured",
            "stock.reserved",
            "order.packed",
            "shipment.dispatched",
        ]:
            assert pos < event_flow_src.index(later_event), (
                f"order.created should precede {later_event}"
            )


class TestOrderServiceCompensation:
    """order-service must handle the payment.failed rollback path."""

    def test_payment_failed_event_documented(self, arch_readme: str) -> None:
        """payment.failed must appear in the README."""
        assert "payment.failed" in arch_readme

    def test_order_cancellation_documented(self, arch_readme: str) -> None:
        """README must state that order-service cancels on failure."""
        assert "cancel" in arch_readme.lower()

    def test_order_service_named_as_failure_handler(
        self, arch_readme: str
    ) -> None:
        """README must name order-service as the payment.failed handler."""
        assert "order-service" in arch_readme
