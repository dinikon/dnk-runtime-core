from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from collections.abc import Mapping
from hashlib import sha256
from typing import Any
from src.modules.channels.domain.channel.aggregate import Channel
from src.modules.channels.domain.channel.entity.connection import Connection
from src.modules.channels.domain.channel.value_object.settings import (
    ConnectionSettingsVO,
)


class ChannelMapper:
    """Преобразует две строки хранения в один агрегат без SQL и переходов."""

    @staticmethod
    def to_domain(
        row: Mapping[str, Any], connection_row: Mapping[str, Any] | None
    ) -> Channel:
        """Восстанавливает корень вместе с принадлежащей ему Entity."""
        connection = None
        if connection_row:
            data = dict(connection_row)
            data["identifier"] = EntityIdVO(data.pop("id"))
            data.pop("channel_id")
            data.pop("resource_key")
            if data["verification_job_id"] is not None:
                data["verification_job_id"] = EntityIdVO(data["verification_job_id"])
            data["settings"] = ConnectionSettingsVO(
                data.pop("endpoint"), tuple(data.pop("locales")), data.pop("currency")
            )
            data["scope_limitations"] = tuple(data["scope_limitations"])
            connection = Connection.restore(**data)
        data = dict(row)
        data["identifier"] = EntityIdVO(data.pop("id"))
        data["created_by"] = EntityIdVO(data["created_by"])
        data["updated_by"] = EntityIdVO(data["updated_by"])
        return Channel.restore(**data, connection=connection)

    @staticmethod
    def to_values(channel: Channel) -> dict[str, Any]:
        """Извлекает поля корня без проверки возможности изменения."""
        return {
            key: (
                getattr(channel, key).uuid
                if isinstance(getattr(channel, key), EntityIdVO)
                else getattr(channel, key)
            )
            for key in (
                "id",
                "name",
                "platform_kind",
                "is_enabled",
                "is_archived",
                "revision",
                "created_at",
                "updated_at",
                "created_by",
                "updated_by",
            )
        }

    @staticmethod
    def connection_values(channel: Channel) -> dict[str, Any] | None:
        """Извлекает принадлежащую агрегату строку, сохраняя ciphertext."""
        c = channel.connection
        if c is None:
            return None
        return dict(
            id=c.id.uuid,
            channel_id=channel.id.uuid,
            endpoint=c.settings.endpoint,
            locales=list(c.settings.locales),
            currency=c.settings.currency,
            credentials_ciphertext=c.credentials_ciphertext,
            candidate_ciphertext=c.candidate_ciphertext,
            resource_identity=c.resource_identity,
            resource_key=(
                sha256(
                    (channel.platform_kind + ":" + c.resource_identity).encode()
                ).hexdigest()
                if c.resource_identity
                else None
            ),
            verification_status=c.verification_status,
            verification_job_id=(
                c.verification_job_id.uuid if c.verification_job_id else None
            ),
            generation=c.generation,
            is_paused=c.is_paused,
            reason_code=c.reason_code,
            scope_limitations=list(c.scope_limitations),
        )
