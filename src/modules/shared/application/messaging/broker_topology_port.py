from __future__ import annotations

from typing import Protocol

from src.modules.shared.application.messaging.broker_exchange import BrokerExchange
from src.modules.shared.application.messaging.broker_queue import BrokerQueue


class BrokerTopologyPort(Protocol):
    async def declare_exchange(self, exchange: BrokerExchange) -> None: ...

    async def declare_queue(self, queue: BrokerQueue) -> None: ...

    async def bind_queue(
        self,
        *,
        queue: BrokerQueue,
        exchange: BrokerExchange,
        routing_key: str,
    ) -> None: ...


__all__ = ["BrokerTopologyPort"]
