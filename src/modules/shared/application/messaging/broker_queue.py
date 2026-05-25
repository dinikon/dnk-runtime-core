from __future__ import annotations

from dataclasses import dataclass, field

from src.modules.shared.application.messaging.broker_queue_arguments import (
    BrokerQueueArguments,
)


@dataclass(frozen=True, slots=True)
class BrokerQueue:
    name: str
    durable: bool = True
    routing_key: str = ""
    arguments: BrokerQueueArguments = field(default_factory=BrokerQueueArguments)


__all__ = ["BrokerQueue"]
