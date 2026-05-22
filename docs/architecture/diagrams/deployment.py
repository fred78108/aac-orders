"""
Deployment View — Docker Compose stack

Shows every container, its role, and the logical network topology
used in local development.

Run from docs/architecture/:  python diagrams/deployment.py
"""

from diagrams import Cluster, Diagram, Edge
from diagrams.onprem.client import User
from diagrams.onprem.database import PostgreSQL
from diagrams.onprem.inmemory import Redis
from diagrams.onprem.network import Nginx
from diagrams.onprem.queue import RabbitMQ
from diagrams.programming.language import Python

with Diagram(
    "Order Fulfillment — Docker Compose Deployment",
    filename="generated/deployment",
    show=False,
    direction="TB",
    graph_attr={"pad": "0.75", "splines": "ortho", "ranksep": "0.8"},
):
    user = User("Developer / Browser")

    with Cluster("Docker Compose Network  (aac-orders_default)"):
        with Cluster("Ingress"):
            nginx = Nginx("nginx\n:80")

        with Cluster("Application Services"):
            order_svc = Python("order-service\n:8001")
            payment_svc = Python("payment-service\n:8002")
            inventory_svc = Python("inventory-service\n:8003")
            fulfillment_svc = Python("fulfillment-service\n:8004")
            shipping_svc = Python("shipping-service\n:8005")
            notification_svc = Python("notification-service\n:8006")

        with Cluster("Messaging"):
            broker = RabbitMQ("rabbitmq\n:5672  mgmt :15672")

        with Cluster("Data Stores"):
            db_orders = PostgreSQL("postgres-orders\n:5432")
            db_payments = PostgreSQL("postgres-payments\n:5433")
            db_inventory = PostgreSQL("postgres-inventory\n:5434")
            db_fulfillment = PostgreSQL("postgres-fulfillment\n:5435")
            db_shipping = PostgreSQL("postgres-shipping\n:5436")
            db_notifications = PostgreSQL("postgres-notifications\n:5437")
            cache = Redis("redis\n:6379")

    # Traffic entry
    user >> nginx
    nginx >> Edge(label="/:8001") >> order_svc

    # Service ↔ database bindings
    order_svc - db_orders
    payment_svc - db_payments
    inventory_svc - db_inventory
    fulfillment_svc - db_fulfillment
    shipping_svc - db_shipping
    notification_svc - db_notifications

    # Session cache
    nginx >> Edge(style="dashed") >> cache

    # All services connect to broker
    for svc in [
        order_svc,
        payment_svc,
        inventory_svc,
        fulfillment_svc,
        shipping_svc,
        notification_svc,
    ]:
        svc >> Edge(style="dashed") >> broker
