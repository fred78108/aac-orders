from __future__ import annotations

import uuid as _uuid

from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from shared.db import Base


class OrderRow(Base):
    __tablename__ = "orders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    customer_id = Column(UUID(as_uuid=True), nullable=False)
    status = Column(String, nullable=False, default="pending")
    items = relationship("OrderItemRow", back_populates="order", cascade="all, delete-orphan")


class OrderItemRow(Base):
    __tablename__ = "order_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id"), nullable=False)
    sku = Column(String, nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price_cents = Column(Integer, nullable=False)
    order = relationship("OrderRow", back_populates="items")
