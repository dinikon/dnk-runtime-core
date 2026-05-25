from __future__ import annotations

from typing import Protocol

from src.modules.shared.application.messaging.broker_exchange import BrokerExchange
from src.modules.shared.application.messaging.broker_message import BrokerMessage


class BrokerPublisherPort(Protocol):
    async def publish(
        self,
        *,
        exchange: BrokerExchange,
        routing_key: str,
        message: BrokerMessage,
        mandatory: bool = True,
    ) -> None: ...


__all__ = ["BrokerPublisherPort"]
