from dataclasses import dataclass, field
from enum import Enum
from uuid import UUID, uuid4


class ShipmentStatus(Enum):
    PENDING = "pending"
    DISPATCHED = "dispatched"
    FAILED = "failed"


@dataclass
class Shipment:
    order_id: UUID
    carrier: str
    tracking_number: str
    id: UUID = field(default_factory=uuid4)
    status: ShipmentStatus = ShipmentStatus.PENDING
