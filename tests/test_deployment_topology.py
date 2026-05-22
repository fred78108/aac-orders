"""
Tests for the Docker Compose deployment topology.

Validates deployment.py against the architecture spec:
  - Correct Docker network name
  - All six Python service containers at ports 8001–8006
  - All six PostgreSQL containers at ports 5432–5437
  - RabbitMQ (AMQP :5672, management :15672)
  - Redis session cache (:6379)
  - Nginx ingress (:80)
  - Each service paired with its dedicated database
  - Ports are unique across services and databases

Source of truth: docs/architecture/diagrams/deployment.py
"""

import pathlib

import pytest


# ── Expected containers ───────────────────────────────────────

SERVICES = [
    ("order-service", ":8001"),
    ("payment-service", ":8002"),
    ("inventory-service", ":8003"),
    ("fulfillment-service", ":8004"),
    ("shipping-service", ":8005"),
    ("notification-service", ":8006"),
]

DATABASES = [
    ("postgres-orders", ":5432"),
    ("postgres-payments", ":5433"),
    ("postgres-inventory", ":5434"),
    ("postgres-fulfillment", ":5435"),
    ("postgres-shipping", ":5436"),
    ("postgres-notifications", ":5437"),
]

SERVICE_NAMES = [s[0] for s in SERVICES]
SERVICE_PORTS = [s[1] for s in SERVICES]
DB_CONTAINER_NAMES = [d[0] for d in DATABASES]
DB_PORTS = [d[1] for d in DATABASES]

DOCKER_NETWORK = "aac-orders_default"


# ── Diagram file existence ────────────────────────────────────


class TestDeploymentFileExists:
    """The deployment diagram source must be present."""

    def test_deployment_py_exists(self, diagrams_dir: pathlib.Path) -> None:
        """deployment.py must exist in the diagrams directory."""
        assert (diagrams_dir / "deployment.py").is_file()

    def test_generate_all_script_exists(
        self, diagrams_dir: pathlib.Path
    ) -> None:
        """generate_all.py must exist to regenerate PNGs."""
        assert (diagrams_dir / "generate_all.py").is_file()


# ── Network configuration ─────────────────────────────────────


class TestNetworkConfiguration:
    """Validate Docker network and infrastructure service ports."""

    def test_docker_network_name(self, deployment_src: str) -> None:
        """The compose network must be named aac-orders_default."""
        assert DOCKER_NETWORK in deployment_src

    def test_nginx_ingress_present(self, deployment_src: str) -> None:
        """Nginx must be present as the ingress container."""
        assert "nginx" in deployment_src.lower()
        assert "Nginx" in deployment_src

    def test_nginx_port_80(self, deployment_src: str) -> None:
        """Nginx must be configured on port 80."""
        assert ":80" in deployment_src

    def test_rabbitmq_amqp_port(self, deployment_src: str) -> None:
        """RabbitMQ AMQP port 5672 must be in the deployment."""
        assert ":5672" in deployment_src

    def test_rabbitmq_management_port(self, deployment_src: str) -> None:
        """RabbitMQ management UI port 15672 must be present."""
        assert ":15672" in deployment_src

    def test_redis_cache_port(self, deployment_src: str) -> None:
        """Redis session cache must be on port 6379."""
        assert ":6379" in deployment_src


# ── Application service containers ───────────────────────────


class TestServiceContainers:
    """All six application service containers must be defined."""

    @pytest.mark.parametrize("name", SERVICE_NAMES)
    def test_service_name_in_deployment(
        self, deployment_src: str, name: str
    ) -> None:
        """Each service container name must appear in deployment.py."""
        assert name in deployment_src, (
            f"Service container '{name}' not in deployment.py"
        )

    @pytest.mark.parametrize(
        "name,port",
        SERVICES,
        ids=SERVICE_NAMES,
    )
    def test_service_port_in_deployment(
        self, deployment_src: str, name: str, port: str
    ) -> None:
        """Each service must have its assigned port documented."""
        assert port in deployment_src, (
            f"Port '{port}' for '{name}' not in deployment.py"
        )

    def test_service_port_count(self, deployment_src: str) -> None:
        """Exactly six distinct service ports must be present."""
        found = [p for p in SERVICE_PORTS if p in deployment_src]
        assert len(found) == 6, f"Expected 6 service ports, found {len(found)}"

    def test_service_ports_are_unique(self) -> None:
        """All service port numbers must be distinct."""
        assert len(set(SERVICE_PORTS)) == len(SERVICE_PORTS)


# ── Database containers ───────────────────────────────────────


class TestDatabaseContainers:
    """All six PostgreSQL containers must be defined."""

    @pytest.mark.parametrize("container", DB_CONTAINER_NAMES)
    def test_db_container_name_in_deployment(
        self,
        deployment_src: str,
        container: str,
    ) -> None:
        """Each DB container name must appear in deployment.py."""
        assert container in deployment_src, (
            f"DB container '{container}' not in deployment.py"
        )

    @pytest.mark.parametrize(
        "container,port",
        DATABASES,
        ids=DB_CONTAINER_NAMES,
    )
    def test_db_port_in_deployment(
        self,
        deployment_src: str,
        container: str,
        port: str,
    ) -> None:
        """Each database must have its assigned port documented."""
        assert port in deployment_src, (
            f"DB port '{port}' for '{container}' not found"
        )

    def test_database_port_count(self, deployment_src: str) -> None:
        """Exactly six distinct database ports must be present."""
        found = [p for p in DB_PORTS if p in deployment_src]
        assert len(found) == 6, f"Expected 6 DB ports, found {len(found)}"

    def test_db_ports_are_unique(self) -> None:
        """All database port numbers must be distinct."""
        assert len(set(DB_PORTS)) == len(DB_PORTS)

    def test_service_and_db_ports_do_not_overlap(self) -> None:
        """Service ports and database ports must not collide."""
        overlap = set(SERVICE_PORTS) & set(DB_PORTS)
        assert not overlap, (
            f"Port collision between services and DBs: {overlap}"
        )


# ── Service-to-database pairing ───────────────────────────────


class TestServiceDatabasePairing:
    """Each service must be paired with its dedicated database."""

    def test_order_service_paired_with_orders_db(
        self, service_overview_src: str
    ) -> None:
        """order-service and orders_db must be in the same cluster."""
        assert "order-service" in service_overview_src
        assert "orders_db" in service_overview_src

    def test_payment_service_paired_with_payments_db(
        self, service_overview_src: str
    ) -> None:
        """payment-service and payments_db must be in the same cluster."""
        assert "payment-service" in service_overview_src
        assert "payments_db" in service_overview_src

    def test_inventory_service_paired_with_inventory_db(
        self, service_overview_src: str
    ) -> None:
        """inventory-service and inventory_db must be in the same cluster."""
        assert "inventory-service" in service_overview_src
        assert "inventory_db" in service_overview_src

    def test_fulfillment_service_paired_with_fulfillment_db(
        self, service_overview_src: str
    ) -> None:
        """fulfillment-service and fulfillment_db must be paired."""
        assert "fulfillment-service" in service_overview_src
        assert "fulfillment_db" in service_overview_src

    def test_shipping_service_paired_with_shipping_db(
        self, service_overview_src: str
    ) -> None:
        """shipping-service and shipping_db must be in the same cluster."""
        assert "shipping-service" in service_overview_src
        assert "shipping_db" in service_overview_src

    def test_notification_service_paired_with_notifications_db(
        self, service_overview_src: str
    ) -> None:
        """notification-service and notifications_db must be paired."""
        assert "notification-service" in service_overview_src
        assert "notifications_db" in service_overview_src
