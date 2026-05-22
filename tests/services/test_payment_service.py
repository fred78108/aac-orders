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
"""


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
