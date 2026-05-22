from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


@dataclass
class Event:
    event_id: UUID = field(default_factory=uuid4)
    occurred_at: datetime = field(default_factory=_now)


@dataclass
class OrderCreatedEvent(Event):
    order_id: UUID | None = None
    customer_id: UUID | None = None
    total_cents: int = 0


@dataclass
class PaymentCapturedEvent(Event):
    order_id: UUID | None = None
    payment_id: UUID | None = None
    amount_cents: int = 0


@dataclass
class PaymentFailedEvent(Event):
    order_id: UUID | None = None
    reason: str = ""


@dataclass
class PaymentRefundRequestedEvent(Event):
    order_id: UUID | None = None
    payment_id: UUID | None = None
    amount_cents: int = 0


@dataclass
class StockReservedEvent(Event):
    order_id: UUID | None = None
    reservation_id: UUID | None = None


@dataclass
class StockInsufficientEvent(Event):
    order_id: UUID | None = None
    sku: str = ""


@dataclass
class OrderPackedEvent(Event):
    order_id: UUID | None = None
    fulfillment_id: UUID | None = None


@dataclass
class ShipmentDispatchedEvent(Event):
    order_id: UUID | None = None
    shipment_id: UUID | None = None
    tracking_number: str = ""


@dataclass
class ShipmentFailedEvent(Event):
    order_id: UUID | None = None
    shipment_id: UUID | None = None
    reason: str = ""


@dataclass
class OrderReturnInitiatedEvent(Event):
    order_id: UUID | None = None
    shipment_id: UUID | None = None
