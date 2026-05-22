from __future__ import annotations

import uuid as _uuid

from sqlalchemy import Column, String
from sqlalchemy.dialects.postgresql import JSON, UUID

from shared.db import Base


class FulfillmentOrderRow(Base):
    __tablename__ = "fulfillment_orders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    order_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    items = Column(JSON, nullable=False, default=list)
    status = Column(String, nullable=False, default="queued")
