from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

BrokerExchangeType = Literal["direct", "topic", "fanout", "headers"]


@dataclass(frozen=True, slots=True)
class BrokerExchange:
    name: str
    type: BrokerExchangeType
    durable: bool = True


__all__ = [
    "BrokerExchange",
    "BrokerExchangeType",
]
