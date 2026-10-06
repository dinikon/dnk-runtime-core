from src.modules.channels.domain.aggregate import Channel
from src.modules.channels.domain.value_object.identifier import ChannelIdVO
from src.modules.channels.domain.value_object.kind import ChannelKind
from src.modules.channels.domain.value_object.status import ChannelStatus
from src.modules.channels.domain.value_object.settings import ConnectionSettings
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


def to_values(channel: Channel):
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


def restore_channel(row):
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
