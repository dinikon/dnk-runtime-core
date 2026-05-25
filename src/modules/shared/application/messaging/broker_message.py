from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class BrokerMessage:
    """Broker-neutral message payload and metadata."""

    payload: Mapping[str, Any]
    headers: Mapping[str, str] = field(default_factory=dict)
    message_id: str | None = None
    correlation_id: str | None = None
    message_type: str | None = None
    timestamp: datetime | None = None
    persistent: bool = True


__all__ = ["BrokerMessage"]
