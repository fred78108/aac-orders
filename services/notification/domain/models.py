from dataclasses import dataclass, field
from enum import Enum
from uuid import UUID, uuid4


class NotificationChannel(Enum):
    EMAIL = "email"
    SMS = "sms"


class NotificationStatus(Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"


@dataclass
class Notification:
    recipient: str
    channel: NotificationChannel
    subject: str
    body: str
    id: UUID = field(default_factory=uuid4)
    status: NotificationStatus = NotificationStatus.PENDING
