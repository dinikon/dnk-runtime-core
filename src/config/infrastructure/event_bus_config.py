from __future__ import annotations

from pydantic import BaseModel, Field, PositiveFloat, PositiveInt
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
    publisher_worker_enabled: bool = Field(
        default=False,
        description="Enables the long-running integration outbox publisher worker.",
    )
    publisher_idle_sleep_seconds: PositiveFloat = Field(
        default=0.5,
        description="Sleep interval when the publisher worker finds no due events.",
    )
    publisher_error_sleep_seconds: PositiveFloat = Field(
        default=5.0,
        description="Sleep interval after an unexpected publisher worker error.",
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
