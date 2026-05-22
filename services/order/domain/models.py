from dataclasses import dataclass, field
from enum import Enum
from uuid import UUID, uuid4


class OrderStatus(Enum):
    PENDING = "pending"
    PAYMENT_PROCESSING = "payment_processing"
    PAID = "paid"
    PACKED = "packed"
    DISPATCHED = "dispatched"
    CANCELLED = "cancelled"


@dataclass
class OrderItem:
    sku: str
    quantity: int
    unit_price_cents: int


@dataclass
class Order:
    customer_id: UUID
    items: list[OrderItem]
    id: UUID = field(default_factory=uuid4)
    status: OrderStatus = OrderStatus.PENDING

    @property
    def total_cents(self) -> int:
        return sum(i.quantity * i.unit_price_cents for i in self.items)
