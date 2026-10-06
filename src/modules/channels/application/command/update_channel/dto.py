from dataclasses import dataclass
from datetime import datetime
from uuid import UUID
from typing import Self
from src.modules.channels.domain.aggregate import Channel
from src.modules.channels.domain.value_object.channel_type import ChannelType


@dataclass(frozen=True, slots=True)
class UpdateChannelResultDTO:
    """Передаёт состояние изменённого канала до commit внешнего UoW."""

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

    @classmethod
    def from_channel(cls, channel: Channel, channel_type: ChannelType) -> Self:
        """Формирует безопасный результат команды из агрегата и категории реестра."""
        return cls(
            id=channel.id.uuid,
            name=channel.name,
            kind=channel.kind.value,
            type=channel_type.value,
            config_version=channel.config_version,
            connection_settings=dict(channel.settings.public),
            configured_secret_fields=channel.settings.secret_fields,
            is_active=channel.is_active,
            status=channel.status.value,
            created_at=channel.created_at,
            updated_at=channel.updated_at,
            created_by=channel.created_by.uuid,
            updated_by=channel.updated_by.uuid,
        )
