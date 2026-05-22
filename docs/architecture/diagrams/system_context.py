"""
C4 Level 1 — System Context

Who interacts with the platform, and which external systems does it depend on.
Run from docs/architecture/:  python diagrams/system_context.py
"""

from diagrams import Cluster, Diagram, Edge
from diagrams.onprem.client import User
from diagrams.onprem.compute import Server
from diagrams.onprem.network import Nginx

with Diagram(
    "Order Fulfillment — System Context",
    filename="generated/system_context",
    show=False,
    direction="TB",
    graph_attr={"pad": "0.75", "splines": "curved", "fontsize": "14"},
):
    customer = User("Customer\n(web / mobile)")

    with Cluster("AAC Order Fulfillment System"):
        platform = Nginx("API Gateway\n:8080")

    with Cluster("External Services"):
        payment_gw = Server("Payment Gateway\n(Stripe)")
        carrier = Server("Shipping Carrier\n(FedEx / UPS)")
        email_sms = Server("Comms Provider\n(SendGrid / Twilio)")

    (
        customer
        >> Edge(label="place order, track shipment\n[HTTPS/REST]")
        >> platform
    )
    platform >> Edge(label="authorise & capture charge\n[REST]") >> payment_gw
    platform >> Edge(label="create label, poll tracking\n[REST]") >> carrier
    platform >> Edge(label="send email / SMS\n[REST]") >> email_sms
