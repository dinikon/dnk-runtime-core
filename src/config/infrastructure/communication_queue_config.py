from __future__ import annotations

from pydantic import BaseModel, Field, PositiveInt
from pydantic_settings import BaseSettings


class CommunicationQueueSettings(BaseModel):
    enabled: bool = Field(
        default=False,
        description="Enable RabbitMQ-backed communication delivery queue.",
    )
    queue_name: str = Field(
        default="communication.outbound.send",
        description="RabbitMQ queue name for outbound communication jobs.",
    )
    exchange_name: str = Field(
        default="communication.outbound",
        description="RabbitMQ direct exchange name for outbound communication jobs.",
    )
    routing_key: str = Field(
        default="send",
        description="RabbitMQ routing key for outbound communication jobs.",
    )
    prefetch: PositiveInt = Field(
        default=20,
        description="Maximum unacknowledged messages per worker channel.",
    )
    workers: PositiveInt = Field(
        default=10,
        description="Recommended number of worker processes/instances.",
    )
    processing_lease_seconds: PositiveInt = Field(
        default=300,
        description="Seconds before a SENDING outbound message is considered stuck.",
    )
    republish_after_seconds: PositiveInt = Field(
        default=60,
        description="Seconds before an unpublished QUEUED job can be republished.",
    )

    @property
    def dlx_exchange_name(self) -> str:
        return f"{self.exchange_name}.dlx"

    @property
    def dlq_name(self) -> str:
        return f"{self.queue_name}.dlq"

    @property
    def dlq_routing_key(self) -> str:
        return f"{self.routing_key}.dlq"


class CommunicationQueueConfig(BaseSettings):
    COMMUNICATION_QUEUE: CommunicationQueueSettings = Field(
        default_factory=CommunicationQueueSettings,
        description="Communication delivery queue settings.",
    )


__all__ = [
    "CommunicationQueueConfig",
    "CommunicationQueueSettings",
]
