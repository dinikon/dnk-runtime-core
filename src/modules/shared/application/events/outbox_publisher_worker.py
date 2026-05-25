from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable

from src.modules.shared.application.events.publish_outbox_result_dto import (
    PublishOutboxResultDTO,
)

logger = logging.getLogger(__name__)

PublishOnce = Callable[[], Awaitable[PublishOutboxResultDTO]]


class OutboxPublisherWorker:
    def __init__(
        self,
        *,
        publish_once: PublishOnce,
        idle_sleep_seconds: float,
        error_sleep_seconds: float,
    ) -> None:
        self._publish_once = publish_once
        self._idle_sleep_seconds = idle_sleep_seconds
        self._error_sleep_seconds = error_sleep_seconds
        self._stop_event = asyncio.Event()

    def stop(self) -> None:
        self._stop_event.set()

    async def run_forever(self) -> None:
        logger.info("Integration outbox publisher worker started")

        while not self._stop_event.is_set():
            try:
                result = await self._publish_once()

                if result.scanned == 0:
                    await asyncio.sleep(self._idle_sleep_seconds)
                    continue

                logger.info(
                    "Integration outbox batch published",
                    extra={
                        "scanned": result.scanned,
                        "published": result.published,
                        "failed": result.failed,
                    },
                )

            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Integration outbox publisher worker failed")
                await asyncio.sleep(self._error_sleep_seconds)

        logger.info("Integration outbox publisher worker stopped")


__all__ = ["OutboxPublisherWorker", "PublishOnce"]
