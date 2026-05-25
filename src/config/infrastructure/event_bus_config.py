from __future__ import annotations

from pydantic import BaseModel, Field, PositiveInt
from pydantic_settings import BaseSettings


class EventBusSettings(BaseModel):
    """Shared integration event bus settings."""

    exchange_name: str = Field(
        default="dnk.integration.events",
        description="Durable topic exchange for integration events.",
    )
    publish_limit: PositiveInt = Field(
        default=100,
        description="Default outbox events batch size for management publisher.",
    )
    retry_base_seconds: PositiveInt = Field(
        default=30,
        description="Base seconds for linear outbox publish retry backoff.",
    )
    max_attempts: PositiveInt = Field(
        default=5,
        description="Maximum publish attempts before outbox event is failed.",
    )


class EventBusConfig(BaseSettings):
    """Config group for the shared integration event bus."""

    EVENT_BUS: EventBusSettings = Field(
        default_factory=EventBusSettings,
        description="Shared integration event bus settings.",
    )


__all__ = [
    "EventBusConfig",
    "EventBusSettings",
]
