"""Агрегат одного канала продаж с принадлежащим ему подключением."""

from dataclasses import dataclass
from datetime import datetime

from src.modules.channels.domain.connection import Connection
from src.modules.channels.domain.enum.verification_status import VerificationStatus
from src.modules.channels.domain.error import (
    ChannelRevisionConflictError,
    InvalidChannelStateError,
)
from src.modules.channels.domain.value_object.channel_name import ChannelNameVO
from src.modules.channels.domain.value_object.connection_config import (
    ConnectionConfigVO,
)
from src.modules.channels.domain.value_object.resource_identity import (
    ResourceIdentityVO,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(slots=True)
class Channel:
    """Управляет подключением, ревизией агрегата и аудитом изменений."""

    id: EntityIdVO
    name: ChannelNameVO
    platform_kind: str
    revision: int
    connection: Connection
    created_at: datetime
    updated_at: datetime
    created_by: EntityIdVO
    updated_by: EntityIdVO

    @classmethod
    def create(
        cls,
        *,
        channel_id: EntityIdVO,
        name: ChannelNameVO,
        platform_kind: str,
        connection: Connection,
        actor_id: EntityIdVO,
        now: datetime,
    ) -> "Channel":
        """Создаёт канал только с новым, ещё не проверенным подключением."""
        if not isinstance(connection, Connection):
            raise InvalidChannelStateError("Некорректное подключение канала.")
        connection.require_consistent_state()
        if (
            connection.config_revision != 1
            or connection.identity is not None
            or connection.verification.status is not VerificationStatus.PENDING
        ):
            raise InvalidChannelStateError("Новый канал требует нового подключения.")
        return cls.restore(
            channel_id=channel_id,
            name=name,
            platform_kind=platform_kind,
            revision=1,
            connection=connection,
            created_at=now,
            updated_at=now,
            created_by=actor_id,
            updated_by=actor_id,
        )

    @classmethod
    def restore(
        cls,
        *,
        channel_id: EntityIdVO,
        name: ChannelNameVO,
        platform_kind: str,
        revision: int,
        connection: Connection,
        created_at: datetime,
        updated_at: datetime,
        created_by: EntityIdVO,
        updated_by: EntityIdVO,
    ) -> "Channel":
        """Восстанавливает корень с проверкой собственных инвариантов."""
        if not isinstance(connection, Connection):
            raise InvalidChannelStateError("Некорректное подключение канала.")
        connection.require_consistent_state()
        if (
            not isinstance(channel_id, EntityIdVO)
            or not isinstance(created_by, EntityIdVO)
            or not isinstance(updated_by, EntityIdVO)
            or not isinstance(name, ChannelNameVO)
            or not isinstance(platform_kind, str)
            or not platform_kind.strip()
            or type(revision) is not int
            or revision < 1
            or revision < connection.config_revision
            or not isinstance(created_at, datetime)
            or not isinstance(updated_at, datetime)
        ):
            raise InvalidChannelStateError("Некорректное состояние канала.")
        return cls(
            id=channel_id,
            name=name,
            platform_kind=platform_kind,
            revision=revision,
            connection=connection,
            created_at=created_at,
            updated_at=updated_at,
            created_by=created_by,
            updated_by=updated_by,
        )

    def require_revision(self, expected_revision: int) -> None:
        """Защищает изменение и удаление от перезаписи чужой ревизии."""
        if self.revision != expected_revision:
            raise ChannelRevisionConflictError("Канал уже изменён.")

    def change_settings(
        self,
        *,
        expected_revision: int,
        name: ChannelNameVO | None,
        config: ConnectionConfigVO | None,
        encrypted_credentials: bytes | None,
        job_id: EntityIdVO,
        actor_id: EntityIdVO,
        now: datetime,
    ) -> bool:
        """Атомарно меняет настройки; возвращает необходимость проверки доступа."""
        self.require_revision(expected_revision)
        if (
            (name is not None and not isinstance(name, ChannelNameVO))
            or not isinstance(actor_id, EntityIdVO)
            or not isinstance(now, datetime)
        ):
            raise InvalidChannelStateError("Некорректное изменение настроек канала.")
        next_name = name if name is not None else self.name
        connection_changed = self.connection.replace_access(
            config=config, encrypted_credentials=encrypted_credentials, job_id=job_id
        )
        if next_name != self.name or connection_changed:
            self.name = next_name
            self._touch(actor_id=actor_id, now=now)
        return connection_changed

    def request_verification(
        self, *, job_id: EntityIdVO, actor_id: EntityIdVO, now: datetime
    ) -> None:
        """Начинает новое поколение проверки сохранённого подключения."""
        if not isinstance(actor_id, EntityIdVO) or not isinstance(now, datetime):
            raise InvalidChannelStateError("Некорректный контекст проверки.")
        self.connection.request_verification(job_id=job_id)
        self._touch(actor_id=actor_id, now=now)

    def accepts_result(self, *, job_id: EntityIdVO, config_revision: int) -> bool:
        """Проверяет актуальность результата через принадлежащее подключение."""
        return self.connection.accepts_result(
            job_id=job_id, config_revision=config_revision
        )

    def can_confirm_identity(self, identity: ResourceIdentityVO) -> bool:
        """Определяет, может ли канал подтвердить предложенный магазин."""
        return self.connection.can_confirm_identity(identity)

    def apply_verification(
        self,
        *,
        job_id: EntityIdVO,
        config_revision: int,
        identity: ResourceIdentityVO | None,
        error_code: str | None,
        now: datetime,
    ) -> None:
        """Применяет результат, изменяя аудит только при актуальном поколении."""
        if self.connection.complete_verification(
            job_id=job_id,
            config_revision=config_revision,
            identity=identity,
            error_code=error_code,
            now=now,
        ):
            self._touch(actor_id=self.updated_by, now=now)

    def _touch(self, *, actor_id: EntityIdVO, now: datetime) -> None:
        """Фиксирует одно изменение агрегата и его инициатора."""
        self.revision += 1
        self.updated_at = now
        self.updated_by = actor_id
