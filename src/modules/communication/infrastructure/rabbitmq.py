from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
import logging
from typing import Any
from uuid import UUID

from faststream import FastStream
from faststream.middlewares.acknowledgement.config import AckPolicy
from faststream.rabbit import RabbitMessage

from src.config.infrastructure.communication_queue_config import (
    CommunicationQueueSettings,
)
from src.modules.communication.application.outbound_message.command import (
    ProcessOutboundMessageByIdCommand,
)
from src.modules.communication.application.outbound_message.queue.dto import (
    OutboundMessageJob,
)
from src.modules.communication.application.outbound_message.ports import (
    OutboundMessagePublisherProtocol,
)
from src.modules.communication.application.outbound_message.use_case import (
    ProcessOutboundMessageByIdUseCase,
)
from src.modules.communication.domain.outbound_message import OutboundMessageIdVO
from src.modules.shared import EntityIdVO
from src.modules.shared.application.messaging import (
    BrokerExchange,
    BrokerMessage,
    BrokerPublisherPort,
    BrokerQueue,
    BrokerQueueArguments,
    BrokerTopologyPort,
)
from src.modules.shared.infrastructure.messaging import (
    RabbitMQBrokerProvider,
    RabbitMQTopologyManager,
    to_rabbit_exchange,
    to_rabbit_queue,
)

logger = logging.getLogger(__name__)


def build_communication_exchange(
    settings: CommunicationQueueSettings,
) -> BrokerExchange:
    return BrokerExchange(
        name=settings.exchange_name,
        type="direct",
        durable=True,
    )


def build_communication_dlx(
    settings: CommunicationQueueSettings,
) -> BrokerExchange:
    return BrokerExchange(
        name=settings.dlx_exchange_name,
        type="direct",
        durable=True,
    )


def build_communication_queue(
    settings: CommunicationQueueSettings,
) -> BrokerQueue:
    return BrokerQueue(
        name=settings.queue_name,
        durable=True,
        routing_key=settings.routing_key,
        arguments=BrokerQueueArguments(
            dead_letter_exchange=settings.dlx_exchange_name,
            dead_letter_routing_key=settings.dlq_routing_key,
        ),
    )


def build_communication_dlq(
    settings: CommunicationQueueSettings,
) -> BrokerQueue:
    return BrokerQueue(
        name=settings.dlq_name,
        durable=True,
        routing_key=settings.dlq_routing_key,
    )


async def ensure_communication_topology(
    topology: BrokerTopologyPort,
    settings: CommunicationQueueSettings,
) -> None:
    exchange = build_communication_exchange(settings)
    queue = build_communication_queue(settings)
    dlx = build_communication_dlx(settings)
    dlq = build_communication_dlq(settings)

    await topology.declare_exchange(exchange)
    await topology.declare_queue(queue)
    await topology.bind_queue(
        queue=queue,
        exchange=exchange,
        routing_key=settings.routing_key,
    )

    await topology.declare_exchange(dlx)
    await topology.declare_queue(dlq)
    await topology.bind_queue(
        queue=dlq,
        exchange=dlx,
        routing_key=settings.dlq_routing_key,
    )


class RabbitMQOutboundMessagePublisher(OutboundMessagePublisherProtocol):
    """Enqueues outbound-message delivery jobs to the communication queue."""

    def __init__(
        self,
        *,
        broker_publisher: BrokerPublisherPort,
        settings: CommunicationQueueSettings,
    ) -> None:
        self._broker_publisher = broker_publisher
        self._settings = settings

    async def publish(
        self,
        *,
        tenant_id: UUID,
        outbound_message_id: UUID,
        source: str,
        published_at: datetime,
    ) -> None:
        job = OutboundMessageJob(
            tenant_id=tenant_id,
            outbound_message_id=outbound_message_id,
            published_at=published_at,
            source=source,
        )
        await self._broker_publisher.publish(
            exchange=build_communication_exchange(self._settings),
            routing_key=self._settings.routing_key,
            message=BrokerMessage(
                payload=job.to_payload(),
                headers={
                    "tenant_id": str(tenant_id),
                    "outbound_message_id": str(outbound_message_id),
                    "source": source,
                },
                message_id=str(outbound_message_id),
                message_type="communication.outbound.send",
                timestamp=published_at,
            ),
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
        result = await processor(
            ProcessOutboundMessageByIdCommand(
                tenant_id=EntityIdVO.from_value(job.tenant_id),
                outbound_message_id=OutboundMessageIdVO.from_value(
                    job.outbound_message_id
                ),
            )
        )
    except Exception:
        logger.exception(
            "Communication outbound job failed; requeueing "
            "tenant_id=%s outbound_message_id=%s",
            job.tenant_id,
            job.outbound_message_id,
        )
        await message.nack(requeue=True)
        return
    if getattr(result, "skipped", False):
        logger.warning(
            "Communication outbound job skipped tenant_id=%s outbound_message_id=%s "
            "status=%s error=%s",
            job.tenant_id,
            job.outbound_message_id,
            getattr(result, "status", None),
            getattr(result, "error_message", None),
        )
    await message.ack()


def build_communication_faststream_app(
    *,
    broker_provider: RabbitMQBrokerProvider,
    settings: CommunicationQueueSettings,
    processor: ProcessOutboundMessageByIdUseCase,
) -> FastStream:
    broker = broker_provider.broker
    app = FastStream(broker)
    queue = to_rabbit_queue(build_communication_queue(settings))
    exchange = to_rabbit_exchange(build_communication_exchange(settings))

    @app.after_startup
    async def setup_topology() -> None:
        await ensure_communication_topology(
            RabbitMQTopologyManager(broker_provider),
            settings,
        )

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
