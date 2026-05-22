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
"""


class TestInventoryServiceDiagramPresence:
    """inventory-service must appear in all relevant diagrams."""

    def test_in_service_overview(
        self, service_overview_src: str
    ) -> None:
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

    def test_database_container_name(
        self, deployment_src: str
    ) -> None:
        """The paired DB container must be postgres-inventory."""
        assert "postgres-inventory" in deployment_src

    def test_database_port_5434(
        self, deployment_src: str
    ) -> None:
        """inventory_db must be on port 5434."""
        assert ":5434" in deployment_src

    def test_database_name_in_service_overview(
        self, service_overview_src: str
    ) -> None:
        """inventory_db must appear paired with inventory-service."""
        assert "inventory_db" in service_overview_src


class TestInventoryServiceEvents:
    """inventory-service event subscription and publishing rules."""

    def test_subscribes_to_payment_captured(
        self, event_flow_src: str
    ) -> None:
        """inventory-service must subscribe to payment.captured."""
        assert "payment.captured" in event_flow_src
        assert "inventory_svc" in event_flow_src

    def test_publishes_stock_reserved(
        self, event_flow_src: str
    ) -> None:
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

    def test_stock_insufficient_in_readme(
        self, arch_readme: str
    ) -> None:
        """stock.insufficient must appear in the README."""
        assert "stock.insufficient" in arch_readme

    def test_stock_insufficient_triggers_refund(
        self, arch_readme: str
    ) -> None:
        """README must link stock.insufficient to a refund request."""
        assert "stock.insufficient" in arch_readme
        assert "payment.refund_requested" in arch_readme
