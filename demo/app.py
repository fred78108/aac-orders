import os
from flask import Flask, render_template, request, jsonify
import httpx

app = Flask(__name__)

SERVICES: dict[str, str] = {
    "order":        os.getenv("ORDER_SERVICE_URL",        "http://localhost:8001"),
    "payment":      os.getenv("PAYMENT_SERVICE_URL",      "http://localhost:8002"),
    "inventory":    os.getenv("INVENTORY_SERVICE_URL",    "http://localhost:8003"),
    "fulfillment":  os.getenv("FULFILLMENT_SERVICE_URL",  "http://localhost:8004"),
    "shipping":     os.getenv("SHIPPING_SERVICE_URL",     "http://localhost:8005"),
    "notification": os.getenv("NOTIFICATION_SERVICE_URL", "http://localhost:8006"),
}

RABBITMQ_API  = os.getenv("RABBITMQ_URL", "http://localhost:15672") + "/api"
RABBITMQ_AUTH = ("guest", "guest")
ORDER_GATEWAY = os.getenv("ORDER_GATEWAY_URL", "http://localhost:8080")


@app.route("/")
def index() -> str:
    return render_template("index.html")


@app.route("/api/health")
def aggregate_health():
    results = {}
    for name, base_url in SERVICES.items():
        try:
            r = httpx.get(f"{base_url}/health", timeout=2.0)
            body: dict = {}
            try:
                body = r.json()
            except Exception:
                pass
            results[name] = {"status": "ok" if r.status_code == 200 else "error",
                             "http_status": r.status_code, **body}
        except httpx.ConnectError:
            results[name] = {"status": "down", "error": "connection refused"}
        except httpx.TimeoutException:
            results[name] = {"status": "down", "error": "timeout"}
        except Exception as exc:
            results[name] = {"status": "error", "error": str(exc)[:80]}
    return jsonify(results)


@app.route("/api/orders", methods=["POST"])
def place_order():
    payload = request.get_json(force=True)
    try:
        r = httpx.post(f"{ORDER_GATEWAY}/orders", json=payload, timeout=5.0)
        body = None
        try:
            body = r.json()
        except Exception:
            body = r.text
        return jsonify({"http_status": r.status_code, "body": body})
    except httpx.ConnectError:
        return jsonify({"error": "Cannot reach order gateway — is the stack running?"}), 503
    except httpx.TimeoutException:
        return jsonify({"error": "Request timed out"}), 504
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/api/rabbitmq/queues")
def rabbitmq_queues():
    try:
        r = httpx.get(f"{RABBITMQ_API}/queues", auth=RABBITMQ_AUTH, timeout=3.0)
        return jsonify(r.json())
    except httpx.ConnectError:
        return jsonify({"error": "RabbitMQ not reachable"}), 503
    except Exception as exc:
        return jsonify({"error": str(exc)}), 503


if __name__ == "__main__":
    port = int(os.getenv("PORT", "9000"))
    app.run(host="0.0.0.0", port=port, debug=False)
