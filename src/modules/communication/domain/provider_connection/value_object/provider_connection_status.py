from enum import StrEnum


class ProviderConnectionStatusVO(StrEnum):
    """Value object статуса provider connection."""

    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"
    ARCHIVED = "ARCHIVED"
