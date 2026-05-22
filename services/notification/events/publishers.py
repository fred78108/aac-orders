"""Outbound event publishers for notification-service.

notification-service does not publish domain events — it is a pure consumer
that fans out external notifications (email, SMS) in response to events from
all other services.
"""
