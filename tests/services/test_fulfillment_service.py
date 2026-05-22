"""
Tests for the fulfillment-service bounded context.

fulfillment-service is step 4 of the happy-path saga: it subscribes
to stock.reserved, handles warehouse pick-pack operations, and
publishes order.packed to hand off to shipping.

If a downstream shipment fails, fulfillment-service handles the
compensating event by publishing order.return_initiated to trigger
the return process.

Responsibilities verified here:
  - Present in every architecture diagram
  - Assigned port :8004 and dedicated fulfillment_db (:5435)
  - Subscribes to stock.reserved
  - Publishes order.packed
  - Compensating path: order.return_initiated documented
"""


class TestFulfillmentServiceDiagramPresence:
    """fulfillment-service must appear in all relevant diagrams."""

    def test_in_service_overview(self, service_overview_src: str) -> None:
        """fulfillment-service must be in service_overview.py."""
        assert "fulfillment-service" in service_overview_src

    def test_in_deployment(self, deployment_src: str) -> None:
        """fulfillment-service must be defined in deployment.py."""
        assert "fulfillment-service" in deployment_src

    def test_in_event_flow(self, event_flow_src: str) -> None:
        """fulfillment-service must be defined in event_flow.py."""
        assert "fulfillment-service" in event_flow_src

    def test_service_cluster_in_service_overview(
        self, service_overview_src: str
    ) -> None:
        """A dedicated 'Fulfillment Service' cluster must exist."""
        assert "Fulfillment Service" in service_overview_src


class TestFulfillmentServicePorts:
    """fulfillment-service must use the correct assigned ports."""

    def test_service_port_8004(self, deployment_src: str) -> None:
        """fulfillment-service must be assigned port 8004."""
        assert ":8004" in deployment_src

    def test_database_container_name(self, deployment_src: str) -> None:
        """The paired DB container must be postgres-fulfillment."""
        assert "postgres-fulfillment" in deployment_src

    def test_database_port_5435(self, deployment_src: str) -> None:
        """fulfillment_db must be on port 5435."""
        assert ":5435" in deployment_src

    def test_database_name_in_service_overview(
        self, service_overview_src: str
    ) -> None:
        """fulfillment_db must appear paired with fulfillment-service."""
        assert "fulfillment_db" in service_overview_src


class TestFulfillmentServiceEvents:
    """fulfillment-service event subscription and publishing rules."""

    def test_subscribes_to_stock_reserved(self, event_flow_src: str) -> None:
        """fulfillment-service must subscribe to stock.reserved."""
        assert "stock.reserved" in event_flow_src
        assert "fulfillment_svc" in event_flow_src

    def test_publishes_order_packed(self, event_flow_src: str) -> None:
        """fulfillment-service must publish order.packed."""
        assert "order.packed" in event_flow_src

    def test_order_packed_follows_stock_reserved(
        self, event_flow_src: str
    ) -> None:
        """order.packed must appear after stock.reserved."""
        assert event_flow_src.index("stock.reserved") < (
            event_flow_src.index("order.packed")
        )

    def test_order_packed_precedes_shipment_dispatched(
        self, event_flow_src: str
    ) -> None:
        """order.packed must appear before shipment.dispatched."""
        assert event_flow_src.index("order.packed") < (
            event_flow_src.index("shipment.dispatched")
        )


class TestFulfillmentServiceCompensation:
    """fulfillment-service compensation path must be documented."""

    def test_order_return_initiated_in_readme(self, arch_readme: str) -> None:
        """order.return_initiated must appear in the README."""
        assert "order.return_initiated" in arch_readme

    def test_shipment_failure_triggers_return(self, arch_readme: str) -> None:
        """README must link shipment.failed to order.return_initiated."""
        assert "shipment.failed" in arch_readme
        assert "order.return_initiated" in arch_readme

    def test_fulfillment_named_as_return_handler(
        self, arch_readme: str
    ) -> None:
        """README must name fulfillment-service as the return handler."""
        assert "fulfillment-service" in arch_readme
