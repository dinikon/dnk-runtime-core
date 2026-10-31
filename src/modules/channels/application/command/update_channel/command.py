"""Вход сценария UpdateChannel."""

from dataclasses import dataclass, field
from uuid import UUID

from src.modules.channels.domain.types import JsonObject
from src.modules.channels.domain.value_object.connection_config import (
    ConnectionConfigVO,
)


@dataclass(frozen=True, slots=True)
class UpdateChannelCommand:
    """Передаёт намерение и доверенный контекст tenant."""

    tenant_id: UUID
    actor_id: UUID
    channel_id: UUID
    expected_revision: int
    name: str | None
    config: ConnectionConfigVO | None
    credentials: JsonObject | None = field(repr=False)
