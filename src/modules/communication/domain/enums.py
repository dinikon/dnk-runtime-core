from __future__ import annotations

from enum import StrEnum


class ConnectorType(StrEnum):
    YAML_HTTP = "YAML_HTTP"
    YAML_SMTP = "YAML_SMTP"
    CUSTOM_ADAPTER = "CUSTOM_ADAPTER"


class ConnectorStatus(StrEnum):
    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"
    DEPRECATED = "DEPRECATED"


class ProviderConnectionStatus(StrEnum):
    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"


class ChannelCode(StrEnum):
    SMS = "SMS"
    VIBER = "VIBER"
    EMAIL = "EMAIL"
    CUSTOM = "CUSTOM"


class MessageClass(StrEnum):
    MARKETING = "MARKETING"
    TRANSACTIONAL = "TRANSACTIONAL"
    SERVICE = "SERVICE"
    OTP = "OTP"
    INFO = "INFO"


class TemplateStatus(StrEnum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"


class TemplateVersionStatus(StrEnum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    DEPRECATED = "DEPRECATED"


class RequestStatus(StrEnum):
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELED = "CANCELED"


class OutboundMessageStatus(StrEnum):
    QUEUED = "QUEUED"
    SENDING = "SENDING"
    SENT = "SENT"
    DELIVERED = "DELIVERED"
    OPENED = "OPENED"
    CLICKED = "CLICKED"
    FAILED = "FAILED"
    EXPIRED = "EXPIRED"
    UNDELIVERED = "UNDELIVERED"
    CANCELED = "CANCELED"
    UNKNOWN = "UNKNOWN"


class AttemptStatus(StrEnum):
    STARTED = "STARTED"
    SUCCESS = "SUCCESS"
    RETRYABLE_FAILED = "RETRYABLE_FAILED"
    NON_RETRYABLE_FAILED = "NON_RETRYABLE_FAILED"
    TIMEOUT = "TIMEOUT"


class DeliveryEventType(StrEnum):
    SENT = "SENT"
    DELIVERED = "DELIVERED"
    FAILED = "FAILED"
    EXPIRED = "EXPIRED"
    OPENED = "OPENED"
    CLICKED = "CLICKED"
    WEBHOOK_RECEIVED = "WEBHOOK_RECEIVED"


__all__ = [
    "AttemptStatus",
    "ChannelCode",
    "ConnectorStatus",
    "ConnectorType",
    "DeliveryEventType",
    "MessageClass",
    "OutboundMessageStatus",
    "ProviderConnectionStatus",
    "RequestStatus",
    "TemplateStatus",
    "TemplateVersionStatus",
]
