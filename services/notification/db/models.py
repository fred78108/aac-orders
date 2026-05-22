from __future__ import annotations

import uuid as _uuid

from sqlalchemy import Column, String
from sqlalchemy.dialects.postgresql import UUID

from shared.db import Base


class NotificationRow(Base):
    __tablename__ = "notifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    recipient = Column(String, nullable=False)
    channel = Column(String, nullable=False)
    subject = Column(String, nullable=False)
    body = Column(String, nullable=False)
    status = Column(String, nullable=False, default="pending")
