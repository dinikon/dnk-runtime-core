from dataclasses import dataclass, field
from uuid import UUID


@dataclass(frozen=True, slots=True)
class UpdateChannelCommand:
    """Передаёт параметры на частичное изменение канала с сохранением пропущенных настроек."""

    tenant_id: UUID
    actor_id: UUID
    channel_id: UUID
    name: str | None = None
    is_active: bool | None = None
    config_version: int | None = None
    connection_settings: dict[str, str] | None = field(default=None, repr=False)
