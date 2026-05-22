"""
C4 Level 2 — Container / Service Overview

All microservices, their dedicated databases, the shared message broker and cache.
Run from docs/architecture/:  python diagrams/service_overview.py
"""

from diagrams import Cluster, Diagram, Edge
from diagrams.onprem.client import User
from diagrams.onprem.database import PostgreSQL
from diagrams.onprem.inmemory import Redis
from diagrams.onprem.network import Nginx
from diagrams.onprem.queue import RabbitMQ
from diagrams.programming.language import Python

with Diagram(
    "Order Fulfillment — Service Overview",
    filename="generated/service_overview",
    show=False,
    direction="LR",
    graph_attr={
        "pad": "0.75",
        "splines": "ortho",
        "nodesep": "0.6",
        "ranksep": "1.0",
    },
):
    customer = User("Customer")

    with Cluster("Ingress"):
        gateway = Nginx("API Gateway\n:8080")

    cache = Redis("Session Cache\n(Redis :6379)")
    broker = RabbitMQ("Message Broker\n(RabbitMQ :5672)")

    with Cluster("Order Service"):
        order_svc = Python("order-service")
        order_db = PostgreSQL("orders_db")
        order_svc - order_db

    with Cluster("Payment Service"):
        payment_svc = Python("payment-service")
        payment_db = PostgreSQL("payments_db")
        payment_svc - payment_db

    with Cluster("Inventory Service"):
        inventory_svc = Python("inventory-service")
        inventory_db = PostgreSQL("inventory_db")
        inventory_svc - inventory_db

    with Cluster("Fulfillment Service"):
        fulfillment_svc = Python("fulfillment-service")
        fulfillment_db = PostgreSQL("fulfillment_db")
        fulfillment_svc - fulfillment_db

    with Cluster("Shipping Service"):
        shipping_svc = Python("shipping-service")
        shipping_db = PostgreSQL("shipping_db")
        shipping_svc - shipping_db

    with Cluster("Notification Service"):
        notification_svc = Python("notification-service")
        notification_db = PostgreSQL("notifications_db")
        notification_svc - notification_db

    # Synchronous path: customer → gateway → order service
    customer >> gateway
    gateway >> cache
    gateway >> order_svc

    # Publishers → broker
    for svc in [
        order_svc,
        payment_svc,
        inventory_svc,
        fulfillment_svc,
        shipping_svc,
    ]:
        svc >> Edge(style="dashed") >> broker

    # Broker → subscribers
    for svc in [
        payment_svc,
        inventory_svc,
        fulfillment_svc,
        shipping_svc,
        notification_svc,
    ]:
        broker >> Edge(style="dashed") >> svc
