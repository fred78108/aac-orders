from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from notification.db.models import NotificationRow
from notification.domain.models import Notification, NotificationChannel, NotificationStatus


class NotificationRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._sf = session_factory

    async def save(self, notification: Notification) -> None:
        async with self._sf() as session:
            row = NotificationRow(
                id=notification.id,
                recipient=notification.recipient,
                channel=notification.channel.value,
                subject=notification.subject,
                body=notification.body,
                status=notification.status.value,
            )
            session.add(row)
            await session.commit()

    async def get(self, notification_id: UUID) -> Notification:
        async with self._sf() as session:
            result = await session.execute(
                select(NotificationRow).where(NotificationRow.id == notification_id)
            )
            row = result.scalar_one()
            return Notification(
                id=row.id,  # type: ignore[arg-type]
                recipient=row.recipient,  # type: ignore[arg-type]
                channel=NotificationChannel(row.channel),
                subject=row.subject,  # type: ignore[arg-type]
                body=row.body,  # type: ignore[arg-type]
                status=NotificationStatus(row.status),
            )
