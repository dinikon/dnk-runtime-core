from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class BrokerQueueArguments:
    dead_letter_exchange: str | None = None
    dead_letter_routing_key: str | None = None
    message_ttl_ms: int | None = None
    max_length: int | None = None


__all__ = ["BrokerQueueArguments"]
