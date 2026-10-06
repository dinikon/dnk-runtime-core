from dataclasses import dataclass, field, replace
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
    """Управляет настройками канала, активностью, техническим статусом и аудитом."""

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

    @classmethod
    def create(
        cls,
        *,
        channel_id: ChannelIdVO,
        name: str,
        kind: ChannelKind,
        config_version: int,
        settings: ConnectionSettings,
        actor_id: EntityIdVO,
        now: datetime,
        is_active: bool = True,
    ) -> Self:
        """Создаёт непроверенный канал с начальным аудитом через проверяемую фабрику."""
        return cls.restore(
            id=channel_id,
            name=name,
            kind=kind,
            config_version=config_version,
            settings=settings,
            is_active=is_active,
            status=ChannelStatus.UNVERIFIED,
            created_at=now,
            updated_at=now,
            created_by=actor_id,
            updated_by=actor_id,
        )

    @classmethod
    def restore(
        cls,
        *,
        id: ChannelIdVO,
        name: str,
        kind: ChannelKind,
        config_version: int,
        settings: ConnectionSettings,
        is_active: bool,
        status: ChannelStatus,
        created_at: datetime,
        updated_at: datetime,
        created_by: EntityIdVO,
        updated_by: EntityIdVO,
    ) -> Self:
        """Проверяет сохранённое состояние, сохраняя статус и исходный аудит."""
        if type(id) is not ChannelIdVO:
            raise InvalidChannelError("Invalid channel identifier.")
        if not isinstance(kind, ChannelKind) or not isinstance(status, ChannelStatus):
            raise InvalidChannelError("Invalid channel kind or status.")
        cls._validate_settings(settings, config_version)
        cls._validate_activity(is_active)
        cls._validate_audit(created_by, created_at)
        cls._validate_audit(updated_by, updated_at)
        return cls(
            id=id,
            name=cls._normalize_name(name),
            kind=kind,
            config_version=config_version,
            settings=settings,
            is_active=is_active,
            status=status,
            created_at=created_at,
            updated_at=updated_at,
            created_by=created_by,
            updated_by=updated_by,
        )

    def rename(self, name: str, *, actor_id: EntityIdVO, now: datetime) -> Self:
        """Меняет название и аудит; одинаковое название сохраняет прежнее состояние."""
        name = self._normalize_name(name)
        self._validate_audit(actor_id, now)
        if name == self.name:
            return self
        return replace(self, name=name, updated_by=actor_id, updated_at=now)

    def set_active(
        self, is_active: bool, *, actor_id: EntityIdVO, now: datetime
    ) -> Self:
        """Включает или выключает канал независимо от технического статуса."""
        self._validate_activity(is_active)
        self._validate_audit(actor_id, now)
        if is_active == self.is_active:
            return self
        return replace(self, is_active=is_active, updated_by=actor_id, updated_at=now)

    def change_settings(
        self,
        settings: ConnectionSettings,
        config_version: int,
        *,
        actor_id: EntityIdVO,
        now: datetime,
    ) -> Self:
        """Заменяет проверенные настройки и сбрасывает проверку при изменении."""
        self._validate_settings(settings, config_version)
        self._validate_audit(actor_id, now)
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

    @staticmethod
    def _normalize_name(name: str) -> str:
        """Проверяет длину названия после удаления крайних пробелов."""
        if not isinstance(name, str) or not 1 <= len(name.strip()) <= 255:
            raise InvalidChannelError(
                "Name must contain 1–255 characters.", field_name="name"
            )
        return name.strip()

    @staticmethod
    def _validate_settings(settings: ConnectionSettings, config_version: int) -> None:
        """Отклоняет неподходящее представление настроек и некорректную версию."""
        if not isinstance(settings, ConnectionSettings):
            raise InvalidChannelError("Invalid connection settings.")
        if type(config_version) is not int or config_version < 1:
            raise InvalidChannelError("Invalid config version.")

    @staticmethod
    def _validate_activity(is_active: bool) -> None:
        """Не допускает числовые значения вместо пользовательского переключателя."""
        if type(is_active) is not bool:
            raise InvalidChannelError("Active flag must be boolean.")

    @staticmethod
    def _validate_audit(actor_id: EntityIdVO, now: datetime) -> None:
        """Проверяет тип инициатора и время с часовым поясом для записи аудита."""
        if type(actor_id) is not EntityIdVO:
            raise InvalidChannelError("Invalid actor identifier.")
        if not isinstance(now, datetime) or now.utcoffset() is None:
            raise InvalidChannelError("Audit time must include a timezone.")
