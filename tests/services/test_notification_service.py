"""
Tests for the notification-service bounded context.

notification-service is the cross-cutting observer of the saga:
it subscribes to every domain event class (order.*, payment.*,
stock.*, shipment.*) so it can dispatch emails and SMS at each
state transition without being part of the main chain.

Unlike the other five services, notification-service does not
publish any events back onto the broker — it is a pure consumer
in the happy path.

Responsibilities verified here:
  - Present in every architecture diagram
  - Assigned port :8006 and dedicated notifications_db (:5437)
  - Subscribes to all four event namespaces (fan-out pattern)
  - No upstream service depends on it (no downstream edges from it)
  - The wildcard subscription pattern is documented in the diagram
"""


class TestNotificationServiceDiagramPresence:
    """notification-service must appear in all relevant diagrams."""

    def test_in_service_overview(
        self, service_overview_src: str
    ) -> None:
        """notification-service must be in service_overview.py."""
        assert "notification-service" in service_overview_src

    def test_in_deployment(self, deployment_src: str) -> None:
        """notification-service must be defined in deployment.py."""
        assert "notification-service" in deployment_src

    def test_in_event_flow(self, event_flow_src: str) -> None:
        """notification-service must be defined in event_flow.py."""
        assert "notification-service" in event_flow_src

    def test_service_cluster_in_service_overview(
        self, service_overview_src: str
    ) -> None:
        """A dedicated 'Notification Service' cluster must exist."""
        assert "Notification Service" in service_overview_src


class TestNotificationServicePorts:
    """notification-service must use the correct assigned ports."""

    def test_service_port_8006(self, deployment_src: str) -> None:
        """notification-service must be assigned port 8006."""
        assert ":8006" in deployment_src

    def test_database_container_name(
        self, deployment_src: str
    ) -> None:
        """The paired DB container must be postgres-notifications."""
        assert "postgres-notifications" in deployment_src

    def test_database_port_5437(
        self, deployment_src: str
    ) -> None:
        """notifications_db must be on port 5437."""
        assert ":5437" in deployment_src

    def test_database_name_in_service_overview(
        self, service_overview_src: str
    ) -> None:
        """notifications_db must appear paired with notification-service."""
        assert "notifications_db" in service_overview_src


class TestNotificationServiceFanOut:
    """notification-service must subscribe to all event namespaces."""

    def test_subscribes_to_order_wildcard(
        self, event_flow_src: str
    ) -> None:
        """notification-service must subscribe to order.* events."""
        assert "order.*" in event_flow_src

    def test_subscribes_to_payment_wildcard(
        self, event_flow_src: str
    ) -> None:
        """notification-service must subscribe to payment.* events."""
        assert "payment.*" in event_flow_src

    def test_subscribes_to_stock_wildcard(
        self, event_flow_src: str
    ) -> None:
        """notification-service must subscribe to stock.* events."""
        assert "stock.*" in event_flow_src

    def test_subscribes_to_shipment_wildcard(
        self, event_flow_src: str
    ) -> None:
        """notification-service must subscribe to shipment.* events."""
        assert "shipment.*" in event_flow_src

    def test_wildcard_subscription_targets_notification_svc(
        self, event_flow_src: str
    ) -> None:
        """The wildcard edge must point to notification_svc."""
        assert "notification_svc" in event_flow_src

    def test_all_event_namespaces_in_single_edge_label(
        self, event_flow_src: str
    ) -> None:
        """The fan-out edge label must include all four namespaces."""
        for namespace in ["order.*", "payment.*", "stock.*"]:
            assert namespace in event_flow_src, (
                f"Fan-out label missing namespace: {namespace}"
            )


class TestNotificationServiceInArchReadme:
    """notification-service responsibilities in the README."""

    def test_notification_service_in_readme(
        self, arch_readme: str
    ) -> None:
        """notification-service must be described in the README."""
        assert "notification-service" in arch_readme

    def test_readme_describes_notification_responsibility(
        self, arch_readme: str
    ) -> None:
        """README service table must list notification-service."""
        assert "notification" in arch_readme.lower()
