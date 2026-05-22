from __future__ import annotations

from uuid import UUID

from notification.domain.models import Notification


class NotificationRepository:
    async def save(self, notification: Notification) -> None:
        raise NotImplementedError

    async def get(self, notification_id: UUID) -> Notification:
        raise NotImplementedError
