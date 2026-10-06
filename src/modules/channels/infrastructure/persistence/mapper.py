from typing import Any

from src.modules.channels.domain.aggregate import Channel
from src.modules.channels.domain.value_object.identifier import ChannelIdVO
from src.modules.channels.domain.value_object.kind import ChannelKind
from src.modules.channels.domain.value_object.status import ChannelStatus
from src.modules.channels.domain.value_object.settings import ConnectionSettings
from src.modules.channels.infrastructure.persistence.models.channel import ChannelModel
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class ChannelMapper:
    """Преобразует агрегат и SQL-представление без I/O и бизнес-правил."""

    @staticmethod
    def to_insert_values(channel: Channel) -> dict[str, Any]:
        """Извлекает все поля нового агрегата, включая запечатанные credentials."""
        return dict(
            id=channel.id.uuid,
            name=channel.name,
            kind=channel.kind.value,
            config_version=channel.config_version,
            connection_settings=dict(channel.settings.public),
            encrypted_secrets=channel.settings.encrypted_secrets,
            configured_secret_fields=list(channel.settings.secret_fields),
            is_active=channel.is_active,
            status=channel.status.value,
            created_at=channel.created_at,
            updated_at=channel.updated_at,
            created_by=channel.created_by.uuid,
            updated_by=channel.updated_by.uuid,
        )

    @staticmethod
    def to_update_values(channel: Channel) -> dict[str, Any]:
        """Извлекает изменяемые поля, сохраняя kind и исходный аудит создания."""
        values = ChannelMapper.to_insert_values(channel)
        for key in ("id", "kind", "created_at", "created_by"):
            values.pop(key)
        return values

    @staticmethod
    def to_domain(row: ChannelModel) -> Channel:
        """Восстанавливает агрегат через явную фабрику без расшифровки credentials."""
        return Channel.restore(
            id=ChannelIdVO.from_value(row.id),
            name=row.name,
            kind=ChannelKind(row.kind),
            config_version=row.config_version,
            settings=ConnectionSettings(
                row.connection_settings,
                row.encrypted_secrets,
                tuple(row.configured_secret_fields),
            ),
            is_active=row.is_active,
            status=ChannelStatus(row.status),
            created_at=row.created_at,
            updated_at=row.updated_at,
            created_by=EntityIdVO.from_value(row.created_by),
            updated_by=EntityIdVO.from_value(row.updated_by),
        )
