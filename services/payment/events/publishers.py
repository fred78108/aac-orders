"""Outbound event publishers for payment-service."""
from shared.events import PaymentCapturedEvent, PaymentRefundRequestedEvent


async def publish_payment_captured(event: PaymentCapturedEvent) -> None:
    """Publish payment.captured after a successful charge."""
    raise NotImplementedError


async def publish_payment_refund_requested(event: PaymentRefundRequestedEvent) -> None:
    """Publish payment.refund_requested to trigger a refund flow."""
    raise NotImplementedError
