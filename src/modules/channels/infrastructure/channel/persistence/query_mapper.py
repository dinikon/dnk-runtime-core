from collections.abc import Mapping
from typing import Any

from src.modules.channels.application.channel.query.get_channel.dto import (
    ChannelDetailsDTO,
)
from src.modules.channels.application.channel.query.list_channels.dto import (
    ChannelListItemDTO,
)
from src.modules.channels.domain.channel.value_object.channel_type import ChannelType


class ChannelQueryMapper:
    """Преобразует безопасные SQL-проекции в DTO без восстановления агрегата."""

    @staticmethod
    def to_details(
        row: Mapping[str, Any], channel_type: ChannelType
    ) -> ChannelDetailsDTO:
        """Собирает карточку из публичных полей и категории платформы."""
        return ChannelDetailsDTO(
            id=row["id"],
            name=row["name"],
            kind=row["kind"],
            type=channel_type.value,
            config_version=row["config_version"],
            connection_settings=dict(row["connection_settings"]),
            configured_secret_fields=tuple(row["configured_secret_fields"]),
            is_active=row["is_active"],
            status=row["status"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            created_by=row["created_by"],
            updated_by=row["updated_by"],
        )

    @staticmethod
    def to_list_item(
        row: Mapping[str, Any], channel_type: ChannelType
    ) -> ChannelListItemDTO:
        """Собирает строку списка, явно ограничивая состав безопасной проекции."""
        return ChannelListItemDTO(
            id=row["id"],
            name=row["name"],
            kind=row["kind"],
            type=channel_type.value,
            config_version=row["config_version"],
            connection_settings=dict(row["connection_settings"]),
            configured_secret_fields=tuple(row["configured_secret_fields"]),
            is_active=row["is_active"],
            status=row["status"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            created_by=row["created_by"],
            updated_by=row["updated_by"],
        )
