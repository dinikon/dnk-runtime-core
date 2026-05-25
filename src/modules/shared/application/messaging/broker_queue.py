from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class BrokerQueue:
    name: str
    durable: bool = True
    routing_key: str | None = None
    arguments: Mapping[str, Any] = field(default_factory=dict)


__all__ = ["BrokerQueue"]
