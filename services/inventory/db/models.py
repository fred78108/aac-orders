from __future__ import annotations

import uuid as _uuid

from sqlalchemy import Column, Integer, String
from sqlalchemy.dialects.postgresql import UUID

from shared.db import Base


class InventoryItemRow(Base):
    __tablename__ = "inventory_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    sku = Column(String, nullable=False, unique=True, index=True)
    quantity_available = Column(Integer, nullable=False, default=0)


class ReservationRow(Base):
    __tablename__ = "reservations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    reservation_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    order_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    sku = Column(String, nullable=False)
    quantity_reserved = Column(Integer, nullable=False)
