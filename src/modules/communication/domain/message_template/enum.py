from __future__ import annotations

from enum import StrEnum


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


__all__ = [
    "ChannelCode",
    "MessageClass",
    "TemplateStatus",
    "TemplateVersionStatus",
]

