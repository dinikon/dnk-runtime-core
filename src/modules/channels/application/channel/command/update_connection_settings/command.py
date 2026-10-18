from dataclasses import dataclass, field
from uuid import UUID
from src.modules.channels.domain.channel.value_object.settings import (
    ConnectionSettingsVO,
)


@dataclass(frozen=True, slots=True)
class UpdateConnectionSettingsCommand:
    """Передаёт намерение update_connection_settings с доверенным контекстом."""

    tenant_id: UUID
    actor_id: UUID
    channel_id: UUID
    revision: int
    settings: ConnectionSettingsVO
    credentials: dict[str, str] | None = field(default=None, repr=False)
