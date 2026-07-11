from __future__ import annotations

import json
import sys
from collections.abc import Mapping
from typing import Any, TextIO

from faststream import FastStream
from faststream.middlewares.acknowledgement.config import AckPolicy
from faststream.rabbit import RabbitMessage

from src.config.infrastructure.event_bus_config import EventBusSettings
from src.modules.shared.application.messaging import (
    BrokerQueue,
    BrokerTopologyPort,
)
from src.modules.shared.domain.events import IntegrationEvent
from src.modules.shared.infrastructure.events.rabbitmq_integration_event_publisher import (
    build_event_bus_exchange,
)
from src.modules.shared.infrastructure.messaging import (
    RabbitMQBrokerProvider,
    RabbitMQTopologyManager,
    to_rabbit_exchange,
    to_rabbit_queue,
)

DEFAULT_CONSOLE_WORKER_QUEUE_NAME = "dnk.integration.events.console"
DEFAULT_CONSOLE_WORKER_ROUTING_KEY = "#"


def build_integration_event_console_queue(
    *,
    queue_name: str = DEFAULT_CONSOLE_WORKER_QUEUE_NAME,
    routing_key: str = DEFAULT_CONSOLE_WORKER_ROUTING_KEY,
) -> BrokerQueue:
    return BrokerQueue(
        name=queue_name,
        durable=True,
        routing_key=routing_key,
    )


async def ensure_integration_event_console_topology(
    *,
    topology: BrokerTopologyPort,
    settings: EventBusSettings,
    queue_name: str = DEFAULT_CONSOLE_WORKER_QUEUE_NAME,
    routing_key: str = DEFAULT_CONSOLE_WORKER_ROUTING_KEY,
) -> None:
    exchange = build_event_bus_exchange(settings)
    queue = build_integration_event_console_queue(
        queue_name=queue_name,
        routing_key=routing_key,
    )

    await topology.declare_exchange(exchange)
    await topology.declare_queue(queue)
    await topology.bind_queue(
        queue=queue,
        exchange=exchange,
        routing_key=routing_key,
    )


async def handle_integration_event_console_message(
    *,
    payload: Mapping[str, Any],
    message: RabbitMessage,
    output: TextIO | None = None,
) -> None:
    stream = output or sys.stdout
    try:
        event = IntegrationEvent.from_payload(payload)
    except Exception as exc:
        print("Invalid integration event received", file=stream)
        print(f"error={exc}", file=stream)
        print(
            "raw_payload="
            + json.dumps(
                dict(payload), ensure_ascii=False, sort_keys=True, default=str
            ),
            file=stream,
        )
        stream.flush()
        await message.reject(requeue=False)
        return

    print("Integration event received", file=stream)
    print(f"event_id={event.event_id}", file=stream)
    print(f"event_type={event.event_type}", file=stream)
    print(f"tenant_id={event.tenant_id}", file=stream)
    print(f"aggregate_type={event.aggregate_type}", file=stream)
    print(f"aggregate_id={event.aggregate_id}", file=stream)
    print(
        "raw_payload="
        + json.dumps(dict(payload), ensure_ascii=False, sort_keys=True, default=str),
        file=stream,
    )
    stream.flush()
    await message.ack()


def build_integration_event_console_worker_app(
    *,
    broker_provider: RabbitMQBrokerProvider,
    settings: EventBusSettings,
    queue_name: str = DEFAULT_CONSOLE_WORKER_QUEUE_NAME,
    routing_key: str = DEFAULT_CONSOLE_WORKER_ROUTING_KEY,
    output: TextIO | None = None,
) -> FastStream:
    broker = broker_provider.broker
    app = FastStream(broker)
    exchange = build_event_bus_exchange(settings)
    queue = build_integration_event_console_queue(
        queue_name=queue_name,
        routing_key=routing_key,
    )

    @app.after_startup
    async def setup_topology() -> None:
        await ensure_integration_event_console_topology(
            topology=RabbitMQTopologyManager(broker_provider),
            settings=settings,
            queue_name=queue_name,
            routing_key=routing_key,
        )

    @broker.subscriber(
        to_rabbit_queue(queue),
        to_rabbit_exchange(exchange),
        ack_policy=AckPolicy.MANUAL,
        persistent=True,
    )
    async def integration_event_console_subscriber(
        payload: dict[str, Any],
        message: RabbitMessage,
    ) -> None:
        await handle_integration_event_console_message(
            payload=payload,
            message=message,
            output=output,
        )

    return app


__all__ = [
    "DEFAULT_CONSOLE_WORKER_QUEUE_NAME",
    "DEFAULT_CONSOLE_WORKER_ROUTING_KEY",
    "build_integration_event_console_queue",
    "build_integration_event_console_worker_app",
    "ensure_integration_event_console_topology",
    "handle_integration_event_console_message",
]
