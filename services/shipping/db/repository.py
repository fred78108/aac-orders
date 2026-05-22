from __future__ import annotations

from uuid import UUID

from shipping.domain.models import Shipment


class ShipmentRepository:
    async def save(self, shipment: Shipment) -> None:
        raise NotImplementedError

    async def get(self, shipment_id: UUID) -> Shipment:
        raise NotImplementedError

    async def update_status(self, shipment_id: UUID, status: str) -> None:
        raise NotImplementedError
