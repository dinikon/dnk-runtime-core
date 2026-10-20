from dataclasses import dataclass
from datetime import datetime
from typing import Self
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.channels.domain.channel.entity.connection import Connection
from src.modules.channels.domain.channel.value_object.settings import (
    ConnectionSettingsVO,
)
from src.modules.channels.domain.error import (
    ChannelsConflictError,
    ChannelsUnavailableError,
    ChannelsValidationError,
    ChannelsNotFoundError,
)


@dataclass(slots=True)
class Channel:
    """Управляет конкретным источником продаж и единственным Connection."""

    id: EntityIdVO
    name: str
    platform_kind: str
    is_enabled: bool
    is_archived: bool
    revision: int
    connection: Connection | None
    created_at: datetime
    updated_at: datetime
    created_by: EntityIdVO
    updated_by: EntityIdVO

    @classmethod
    def create(
        cls,
        identifier: EntityIdVO,
        name: str,
        kind: str,
        actor: EntityIdVO,
        now: datetime,
    ) -> Self:
        """Создаёт источник с выключенной исходящей синхронизацией."""
        return cls.restore(
            identifier,
            name.strip(),
            kind,
            False,
            False,
            1,
            None,
            now,
            now,
            actor,
            actor,
        )

    @classmethod
    def restore(
        cls,
        identifier: EntityIdVO,
        name: str,
        platform_kind: str,
        is_enabled: bool,
        is_archived: bool,
        revision: int,
        connection: Connection | None,
        created_at: datetime,
        updated_at: datetime,
        created_by: EntityIdVO,
        updated_by: EntityIdVO,
    ) -> Self:
        """Проверяет сохранённое состояние без создания новой identity."""
        if (
            not isinstance(identifier, EntityIdVO)
            or not isinstance(created_by, EntityIdVO)
            or (not isinstance(updated_by, EntityIdVO))
            or (type(is_enabled) is not bool)
            or (type(is_archived) is not bool)
            or (is_archived and is_enabled)
            or (not name)
            or (len(name) > 200)
            or (not platform_kind)
            or (revision < 1)
            or (created_at.utcoffset() is None)
            or (updated_at.utcoffset() is None)
        ):
            raise ChannelsValidationError("invalid_channel_state")
        return cls(
            identifier,
            name,
            platform_kind,
            is_enabled,
            is_archived,
            revision,
            connection,
            created_at,
            updated_at,
            created_by,
            updated_by,
        )

    def ensure_revision(self, revision: int) -> None:
        """Отклоняет изменения на устаревшей версии агрегата."""
        if revision != self.revision:
            raise ChannelsConflictError("channel_revision_changed")

    def require_connection(self) -> Connection:
        """Возвращает внутреннее подключение для доменной координации."""
        if self.connection is None:
            raise ChannelsNotFoundError("connection_not_configured")
        return self.connection

    def ensure_network(
        self, generation: int | None = None, verified: bool = True
    ) -> Connection:
        """Проверяет доступность чтения независимо от is_enabled."""
        connection = self.require_connection()
        if self.is_archived or connection.is_paused:
            raise ChannelsUnavailableError("connection_paused_or_archived")
        if generation is not None and connection.generation != generation:
            raise ChannelsConflictError("connection_generation_changed")
        if verified and connection.verification_status != "verified":
            raise ChannelsUnavailableError("connection_not_verified")
        return connection

    def ensure_outbound(self, generation: int) -> Connection:
        """Разрешает исходящую запись только после явного включения канала."""
        connection = self.ensure_network(generation)
        if not self.is_enabled:
            raise ChannelsUnavailableError("outbound_sync_disabled")
        return connection

    def attach_connection(
        self,
        identifier: EntityIdVO,
        settings: ConnectionSettingsVO,
        ciphertext: str,
        actor: EntityIdVO,
        now: datetime,
    ) -> None:
        """Запрещает второе подключение, включая архивный Channel."""
        if self.connection is not None:
            raise ChannelsConflictError("connection_already_exists")
        if self.is_archived:
            raise ChannelsUnavailableError("channel_archived")
        self.connection = Connection.create(identifier, settings, ciphertext)
        self._touch(actor, now)

    def request_verification(
        self, job_id: EntityIdVO, actor: EntityIdVO, now: datetime
    ) -> None:
        """Запускает новую generation проверки только доступного подключения."""
        self.ensure_network(verified=False).request_verification(job_id)
        self._touch(actor, now)

    def update_connection(
        self,
        settings: ConnectionSettingsVO,
        ciphertext: str | None,
        actor: EntityIdVO,
        now: datetime,
    ) -> None:
        """Изменяет настройки внутренней сущности через корень."""
        if self.is_archived:
            raise ChannelsUnavailableError("channel_archived")
        self.require_connection().change_settings(settings, ciphertext)
        self._touch(actor, now)

    def apply_verification(
        self,
        generation: int,
        identity: str | None,
        reason: str | None,
        limitations: tuple[str, ...],
        actor: EntityIdVO,
        now: datetime,
    ) -> None:
        """Применяет только актуальный результат внешней проверки."""
        self.ensure_network(generation, verified=False).apply_verification(
            identity, reason, limitations
        )
        self._touch(actor, now)

    def update_policy(
        self, name: str, is_enabled: bool, actor: EntityIdVO, now: datetime
    ) -> None:
        """Меняет имя и явное разрешение исходящей синхронизации."""
        if type(is_enabled) is not bool or not name.strip() or len(name.strip()) > 200:
            raise ChannelsValidationError("invalid_channel_name")
        if self.is_archived:
            raise ChannelsUnavailableError("channel_archived")
        self.name, self.is_enabled = (name.strip(), is_enabled)
        self._touch(actor, now)

    def pause_connection(self, actor: EntityIdVO, now: datetime) -> None:
        """Приостанавливает все сетевые операции источника."""
        self.require_connection().pause()
        self._touch(actor, now)

    def resume_connection(self, actor: EntityIdVO, now: datetime) -> None:
        """Возобновляет чтение без автоматического включения записи."""
        if self.is_archived:
            raise ChannelsUnavailableError("channel_archived")
        self.require_connection().resume()
        self._touch(actor, now)

    def archive(self, actor: EntityIdVO, now: datetime) -> None:
        """Архивирует источник целиком, сохраняя данные и историю."""
        self.is_archived, self.is_enabled = (True, False)
        if self.connection:
            self.connection.pause()
        self._touch(actor, now)

    def _touch(self, actor: EntityIdVO, now: datetime) -> None:
        """Увеличивает версию и аудит после разрешённого перехода."""
        self.revision += 1
        self.updated_at, self.updated_by = (now, actor)
