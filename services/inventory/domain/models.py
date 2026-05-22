from dataclasses import dataclass, field
from uuid import UUID, uuid4


@dataclass
class StockItem:
    sku: str
    quantity_available: int
    id: UUID = field(default_factory=uuid4)


@dataclass
class StockReservation:
    order_id: UUID
    items: list[StockItem]
    id: UUID = field(default_factory=uuid4)
