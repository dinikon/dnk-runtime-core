from dataclasses import dataclass, replace, field
from datetime import datetime
from typing import Self
from src.modules.channels.domain.error import InvalidChannelError
from src.modules.channels.domain.value_object.identifier import ChannelIdVO
from src.modules.channels.domain.value_object.kind import ChannelKind
from src.modules.channels.domain.value_object.settings import ConnectionSettings
from src.modules.channels.domain.value_object.status import ChannelStatus
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(frozen=True, slots=True)
class Channel:
    """Канал tenant: настройки магазина и независимые активность/проверка."""

    id: ChannelIdVO
    name: str
    kind: ChannelKind
    config_version: int
    settings: ConnectionSettings = field(repr=False)
    is_active: bool
    status: ChannelStatus
    created_at: datetime
    updated_at: datetime
    created_by: EntityIdVO
    updated_by: EntityIdVO

    def __post_init__(self):
        if type(self.id) is not ChannelIdVO:
            raise InvalidChannelError("Invalid channel identifier.")
        if not isinstance(self.name, str) or not 1 <= len(self.name.strip()) <= 255:
            raise InvalidChannelError("Name must contain 1–255 characters.")
        object.__setattr__(self, "name", self.name.strip())
        if not isinstance(self.kind, ChannelKind) or not isinstance(
            self.status, ChannelStatus
        ):
            raise InvalidChannelError("Invalid channel kind or status.")
        if (
            type(self.is_active) is not bool
            or type(self.config_version) is not int
            or self.config_version < 1
        ):
            raise InvalidChannelError("Invalid active flag or config version.")
        if not isinstance(self.settings, ConnectionSettings):
            raise InvalidChannelError("Invalid connection settings.")

    @classmethod
    def create(
        cls,
        *,
        channel_id,
        name,
        kind,
        config_version,
        settings,
        is_active,
        actor_id,
        now,
    ) -> Self:
        return cls(
            channel_id,
            name,
            kind,
            config_version,
            settings,
            is_active,
            ChannelStatus.UNVERIFIED,
            now,
            now,
            actor_id,
            actor_id,
        )

    @classmethod
    def restore(cls, **state) -> Self:
        """Восстанавливает сохранённое состояние с проверкой инвариантов."""
        return cls(**state)

    def rename(self, name: str, *, actor_id, now) -> Self:
        if isinstance(name, str) and name.strip() == self.name:
            return self
        return replace(self, name=name, updated_by=actor_id, updated_at=now)

    def set_active(self, is_active: bool, *, actor_id, now) -> Self:
        if type(is_active) is not bool:
            raise InvalidChannelError("Active flag must be boolean.")
        if is_active == self.is_active:
            return self
        return replace(self, is_active=is_active, updated_by=actor_id, updated_at=now)

    def change_settings(
        self, settings: ConnectionSettings, config_version: int, *, actor_id, now
    ) -> Self:
        if settings == self.settings and config_version == self.config_version:
            return self
        return replace(
            self,
            settings=settings,
            config_version=config_version,
            status=ChannelStatus.UNVERIFIED,
            updated_by=actor_id,
            updated_at=now,
        )
