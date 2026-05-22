from __future__ import annotations

import uuid as _uuid

from sqlalchemy import Column, Integer, String
from sqlalchemy.dialects.postgresql import UUID

from shared.db import Base


class PaymentRow(Base):
    __tablename__ = "payments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    order_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    customer_id = Column(UUID(as_uuid=True), nullable=False)
    amount_cents = Column(Integer, nullable=False)
    status = Column(String, nullable=False, default="pending")
