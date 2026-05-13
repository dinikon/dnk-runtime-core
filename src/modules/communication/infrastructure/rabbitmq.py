from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from faststream import FastStream
from faststream.middlewares.acknowledgement.config import AckPolicy
from faststream.rabbit import (
    Channel,
    ExchangeType,
    RabbitBroker,
    RabbitExchange,
    RabbitMessage,
    RabbitQueue,
)

from src.config.infrastructure.communication_queue_config import (
    CommunicationQueueSettings,
)
from src.modules.communication.application.dto import OutboundMessageJob
from src.modules.communication.application.use_cases import (
    ProcessOutboundMessageByIdCommand,
    ProcessOutboundMessageByIdUseCase,
)
from src.modules.communication.domain.outbound_message import OutboundMessageIdVO
from src.modules.shared import EntityIdVO


def build_communication_exchange(
    settings: CommunicationQueueSettings,
) -> RabbitExchange:
    return RabbitExchange(
        settings.exchange_name,
        type=ExchangeType.DIRECT,
        durable=True,
    )


def build_communication_dlx(
    settings: CommunicationQueueSettings,
) -> RabbitExchange:
    return RabbitExchange(
        settings.dlx_exchange_name,
        type=ExchangeType.DIRECT,
        durable=True,
    )


def build_communication_queue(
    settings: CommunicationQueueSettings,
) -> RabbitQueue:
    return RabbitQueue(
        settings.queue_name,
        durable=True,
        routing_key=settings.routing_key,
        arguments={
            "x-dead-letter-exchange": settings.dlx_exchange_name,
            "x-dead-letter-routing-key": settings.dlq_routing_key,
        },
    )


def build_communication_dlq(
    settings: CommunicationQueueSettings,
) -> RabbitQueue:
    return RabbitQueue(
        settings.dlq_name,
        durable=True,
        routing_key=settings.dlq_routing_key,
    )


async def ensure_communication_topology(
    broker: RabbitBroker,
    settings: CommunicationQueueSettings,
) -> None:
    exchange = await broker.declare_exchange(build_communication_exchange(settings))
    queue = await broker.declare_queue(build_communication_queue(settings))
    await queue.bind(exchange, routing_key=settings.routing_key)

    dlx = await broker.declare_exchange(build_communication_dlx(settings))
    dlq = await broker.declare_queue(build_communication_dlq(settings))
    await dlq.bind(dlx, routing_key=settings.dlq_routing_key)


class RabbitMQOutboundMessagePublisher:
    """Publishes outbound-message jobs to RabbitMQ."""

    def __init__(
        self,
        *,
        broker: RabbitBroker,
        settings: CommunicationQueueSettings,
        manage_broker_lifecycle: bool = False,
    ) -> None:
        self._broker = broker
        self._settings = settings
        self._manage_broker_lifecycle = manage_broker_lifecycle
        self._started = False

    @classmethod
    def from_settings(
        cls,
        settings: CommunicationQueueSettings,
        *,
        manage_broker_lifecycle: bool = False,
    ) -> "RabbitMQOutboundMessagePublisher":
        broker = RabbitBroker(
            settings.rabbitmq_url,
            default_channel=Channel(publisher_confirms=True),
        )
        return cls(
            broker=broker,
            settings=settings,
            manage_broker_lifecycle=manage_broker_lifecycle,
        )

    async def start(self) -> None:
        if self._started:
            return
        await self._broker.start()
        await ensure_communication_topology(self._broker, self._settings)
        self._started = True

    async def close(self) -> None:
        if self._started and self._manage_broker_lifecycle:
            await self._broker.close()
        self._started = False

    async def __aenter__(self) -> "RabbitMQOutboundMessagePublisher":
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.close()

    async def publish(
        self,
        *,
        tenant_id: UUID,
        outbound_message_id: UUID,
        source: str,
        published_at: datetime,
    ) -> None:
        if not self._started:
            await self.start()
        job = OutboundMessageJob(
            tenant_id=tenant_id,
            outbound_message_id=outbound_message_id,
            published_at=published_at,
            source=source,
        )
        await self._broker.publish(
            job.to_payload(),
            exchange=build_communication_exchange(self._settings),
            routing_key=self._settings.routing_key,
            mandatory=True,
            persist=True,
            message_id=str(outbound_message_id),
            timestamp=published_at,
            message_type="communication.outbound.send",
        )


async def handle_outbound_message_job(
    *,
    payload: Mapping[str, Any],
    message: RabbitMessage,
    processor: ProcessOutboundMessageByIdUseCase,
) -> None:
    try:
        job = _parse_outbound_message_job(payload)
    except Exception:
        await message.reject(requeue=False)
        return

    try:
        await processor(
            ProcessOutboundMessageByIdCommand(
                tenant_id=EntityIdVO.from_value(job.tenant_id),
                outbound_message_id=OutboundMessageIdVO.from_value(
                    job.outbound_message_id
                ),
            )
        )
    except Exception:
        await message.nack(requeue=True)
        return
    await message.ack()


def build_communication_faststream_app(
    *,
    settings: CommunicationQueueSettings,
    processor: ProcessOutboundMessageByIdUseCase,
) -> FastStream:
    broker = RabbitBroker(
        settings.rabbitmq_url,
        default_channel=Channel(
            prefetch_count=settings.prefetch,
            publisher_confirms=True,
        ),
    )
    app = FastStream(broker)
    queue = build_communication_queue(settings)
    exchange = build_communication_exchange(settings)

    @app.after_startup
    async def setup_topology() -> None:
        await ensure_communication_topology(broker, settings)

    @broker.subscriber(
        queue,
        exchange,
        ack_policy=AckPolicy.MANUAL,
        persistent=True,
    )
    async def outbound_message_subscriber(
        payload: dict[str, Any],
        message: RabbitMessage,
    ) -> None:
        await handle_outbound_message_job(
            payload=payload,
            message=message,
            processor=processor,
        )

    return app


def _parse_outbound_message_job(payload: Mapping[str, Any]) -> OutboundMessageJob:
    tenant_id = UUID(str(payload["tenant_id"]))
    outbound_message_id = UUID(str(payload["outbound_message_id"]))
    published_at_raw = payload.get("published_at")
    published_at = (
        datetime.fromisoformat(str(published_at_raw))
        if published_at_raw is not None
        else datetime.now(UTC)
    )
    source = str(payload.get("source") or "unknown")
    return OutboundMessageJob(
        tenant_id=tenant_id,
        outbound_message_id=outbound_message_id,
        published_at=published_at,
        source=source,
    )


__all__ = [
    "RabbitMQOutboundMessagePublisher",
    "build_communication_faststream_app",
    "build_communication_queue",
    "build_communication_exchange",
    "build_communication_dlq",
    "build_communication_dlx",
    "ensure_communication_topology",
    "handle_outbound_message_job",
]
