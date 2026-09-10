from __future__ import annotations

import asyncio

from faststream.rabbit import Channel, RabbitBroker

from src.config.infrastructure.rabbitmq_config import RabbitMQSettings


class RabbitMQBrokerProvider:
    def __init__(self, settings: RabbitMQSettings) -> None:
        self._settings = settings
        self._broker: RabbitBroker | None = None
        self._started = False
        self._start_lock = asyncio.Lock()

    @property
    def broker(self) -> RabbitBroker:
        broker = self._broker

        if broker is None:
            broker = RabbitBroker(
                self._settings.url,
                default_channel=Channel(
                    publisher_confirms=self._settings.publisher_confirms,
                    prefetch_count=self._settings.prefetch,
                ),
            )
            self._broker = broker

        return broker

    async def start(self) -> None:
        if self._started:
            return

        async with self._start_lock:
            if self._started:
                return

            broker = self.broker
            if getattr(broker, "running", False):
                self._started = True
                return

            await broker.start()
            self._started = True

    async def close(self) -> None:
        if (
            self._broker is not None
            and self._started
            and getattr(self._broker, "running", True)
        ):
            await self._broker.stop()

        self._started = False
