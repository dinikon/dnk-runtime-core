from __future__ import annotations

from enum import StrEnum


class ConnectorType(StrEnum):
    YAML_HTTP = "YAML_HTTP"
    YAML_SMTP = "YAML_SMTP"
    CUSTOM_ADAPTER = "CUSTOM_ADAPTER"


class ConnectorStatus(StrEnum):
    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"
    ARCHIVED = "ARCHIVED"


__all__ = [
    "ConnectorStatus",
    "ConnectorType",
]
