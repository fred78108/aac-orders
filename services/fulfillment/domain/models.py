from dataclasses import dataclass, field
from enum import Enum
from uuid import UUID, uuid4


class PackingStatus(Enum):
    QUEUED = "queued"
    PACKED = "packed"
    RETURNED = "returned"


@dataclass
class FulfillmentOrder:
    order_id: UUID
    items: list
    id: UUID = field(default_factory=uuid4)
    status: PackingStatus = PackingStatus.QUEUED
