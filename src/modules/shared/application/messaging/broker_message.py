from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class BrokerMessage:
    """Broker-neutral message payload and metadata."""

    body: dict[str, Any]
    headers: Mapping[str, str] | None = None
    message_id: str | None = None
    correlation_id: str | None = None
    content_type: str = "application/json"


__all__ = ["BrokerMessage"]
