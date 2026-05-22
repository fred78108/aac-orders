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
"""


class TestShippingServiceDiagramPresence:
    """shipping-service must appear in all relevant diagrams."""

    def test_in_service_overview(
        self, service_overview_src: str
    ) -> None:
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

    def test_database_container_name(
        self, deployment_src: str
    ) -> None:
        """The paired DB container must be postgres-shipping."""
        assert "postgres-shipping" in deployment_src

    def test_database_port_5436(
        self, deployment_src: str
    ) -> None:
        """shipping_db must be on port 5436."""
        assert ":5436" in deployment_src

    def test_database_name_in_service_overview(
        self, service_overview_src: str
    ) -> None:
        """shipping_db must appear paired with shipping-service."""
        assert "shipping_db" in service_overview_src


class TestShippingServiceEvents:
    """shipping-service event subscription and publishing rules."""

    def test_subscribes_to_order_packed(
        self, event_flow_src: str
    ) -> None:
        """shipping-service must subscribe to order.packed."""
        assert "order.packed" in event_flow_src
        assert "shipping_svc" in event_flow_src

    def test_publishes_shipment_dispatched(
        self, event_flow_src: str
    ) -> None:
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
            assert (
                event_flow_src.index(earlier_event) < pos
            ), (
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

    def test_shipment_failed_in_readme(
        self, arch_readme: str
    ) -> None:
        """shipment.failed must appear in the README."""
        assert "shipment.failed" in arch_readme

    def test_shipment_failure_triggers_return_initiated(
        self, arch_readme: str
    ) -> None:
        """README must link shipment.failed to order.return_initiated."""
        assert "shipment.failed" in arch_readme
        assert "order.return_initiated" in arch_readme
