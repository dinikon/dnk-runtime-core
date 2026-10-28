"""Вход сценария VerifyConnection."""

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class VerifyConnectionCommand:
    """Передаёт намерение и доверенный контекст tenant."""

    tenant_id: UUID
    actor_id: UUID
    channel_id: UUID
