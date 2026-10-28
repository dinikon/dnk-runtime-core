"""Вход сценария CreateChannel."""

from dataclasses import dataclass, field
from uuid import UUID

from src.modules.channels.domain.types import JsonObject
from src.modules.channels.domain.channel.value_object.connection_config import (
    ConnectionConfigVO,
)


@dataclass(frozen=True, slots=True)
class CreateChannelCommand:
    """Передаёт намерение и доверенный контекст tenant."""

    tenant_id: UUID
    actor_id: UUID
    name: str
    platform_kind: str
    config: ConnectionConfigVO
    credentials: JsonObject = field(repr=False)
