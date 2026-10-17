from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ChannelDetailsDTO:
    """Передаёт безопасную карточку канала без credentials."""

    id: UUID
    name: str
    kind: str
    type: str
    config_version: int
    connection_settings: dict[str, str]
    configured_secret_fields: tuple[str, ...]
    is_active: bool
    status: str
    created_at: datetime
    updated_at: datetime
    created_by: UUID
    updated_by: UUID
