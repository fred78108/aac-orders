"""
Event Flow — Choreography-based saga (happy path)

Shows the chain of domain events that carries an order from placement through
to customer notification.  Each service publishes one event; downstream
services subscribe and react, with no central orchestrator.

Run from docs/architecture/:  python diagrams/event_flow.py
"""

from diagrams import Cluster, Diagram, Edge
from diagrams.onprem.client import User
from diagrams.onprem.network import Nginx
from diagrams.onprem.queue import RabbitMQ
from diagrams.programming.language import Python

with Diagram(
    "Order Fulfillment — Event Flow (Happy Path)",
    filename="generated/event_flow",
    show=False,
    direction="LR",
    graph_attr={
        "pad": "0.75", "splines": "curved", "nodesep": "0.5", "ranksep": "1.4"
    },
):
    customer = User("Customer")
    gateway = Nginx("API Gateway")
    broker = RabbitMQ("Message Broker\n(RabbitMQ)")

    with Cluster("1 · Order Domain"):
        order_svc = Python("order-service")

    with Cluster("2 · Payment Domain"):
        payment_svc = Python("payment-service")

    with Cluster("3 · Inventory Domain"):
        inventory_svc = Python("inventory-service")

    with Cluster("4 · Fulfillment Domain"):
        fulfillment_svc = Python("fulfillment-service")

    with Cluster("5 · Shipping Domain"):
        shipping_svc = Python("shipping-service")

    with Cluster("Notification Domain"):
        notification_svc = Python("notification-service")

    # ── Synchronous entry ──────────────────────────────────────────────────
    customer >> Edge(label="POST /orders", color="#27ae60") >> gateway
    gateway >> Edge(label="HTTP", color="#27ae60") >> order_svc

    # ── Published events (service → broker) ───────────────────────────────
    order_svc >> Edge(label="order.created", style="dashed", color="#e67e22") >> broker
    payment_svc >> Edge(label="payment.captured", style="dashed", color="#e67e22") >> broker
    inventory_svc >> Edge(label="stock.reserved", style="dashed", color="#e67e22") >> broker
    fulfillment_svc >> Edge(label="order.packed", style="dashed", color="#e67e22") >> broker
    shipping_svc >> Edge(label="shipment.dispatched", style="dashed", color="#e67e22") >> broker

    # ── Consumed events (broker → subscriber) ─────────────────────────────
    broker >> Edge(label="order.created", style="dashed", color="#2980b9") >> payment_svc
    broker >> Edge(label="payment.captured", style="dashed", color="#2980b9") >> inventory_svc
    broker >> Edge(label="stock.reserved", style="dashed", color="#2980b9") >> fulfillment_svc
    broker >> Edge(label="order.packed", style="dashed", color="#2980b9") >> shipping_svc

    # Notification service subscribes to all status-change events
    all_events = Edge(
        label="order.* / payment.* /\nstock.* / shipment.*",
        style="dashed",
        color="#2980b9",
    )
    broker >> all_events >> notification_svc
