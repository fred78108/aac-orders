from __future__ import annotations

import uuid as _uuid

from sqlalchemy import Column, String
from sqlalchemy.dialects.postgresql import UUID

from shared.db import Base


class ShipmentRow(Base):
    __tablename__ = "shipments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    order_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    carrier = Column(String, nullable=False)
    tracking_number = Column(String, nullable=False)
    status = Column(String, nullable=False, default="pending")
