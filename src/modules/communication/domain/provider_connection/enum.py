from __future__ import annotations

from enum import StrEnum


class ProviderConnectionStatus(StrEnum):
    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"


__all__ = ["ProviderConnectionStatus"]
