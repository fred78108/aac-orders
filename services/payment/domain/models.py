from dataclasses import dataclass, field
from enum import Enum
from uuid import UUID, uuid4


class PaymentStatus(Enum):
    PENDING = "pending"
    CAPTURED = "captured"
    FAILED = "failed"
    REFUNDED = "refunded"


@dataclass
class Payment:
    order_id: UUID
    amount_cents: int
    customer_id: UUID
    id: UUID = field(default_factory=uuid4)
    status: PaymentStatus = PaymentStatus.PENDING
