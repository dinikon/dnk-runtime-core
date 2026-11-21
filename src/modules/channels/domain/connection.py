"""Подключение, жизненным циклом которого управляет Channel."""

from dataclasses import dataclass, field
from datetime import datetime

from src.modules.channels.domain.enum.verification_status import (
    VerificationStatus,
)
from src.modules.channels.domain.error import (
    InvalidChannelStateError,
    InvalidResourceIdentityError,
)
from src.modules.channels.domain.value_object.connection_config import (
    ConnectionConfigVO,
)
from src.modules.channels.domain.value_object.resource_identity import (
    ResourceIdentityVO,
)
from src.modules.channels.domain.value_object.verification import VerificationVO
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(slots=True)
class Connection:
    """Владеет настройками, закреплённым магазином и поколением проверки."""

    id: EntityIdVO
    config: ConnectionConfigVO
    encrypted_credentials: bytes = field(repr=False)
    config_revision: int
    identity: ResourceIdentityVO | None
    verification: VerificationVO

    @classmethod
    def create(
        cls,
        *,
        connection_id: EntityIdVO,
        config: ConnectionConfigVO,
        encrypted_credentials: bytes,
        job_id: EntityIdVO,
    ) -> "Connection":
        """Создаёт первую ожидающую проверку нового подключения."""
        return cls.restore(
            connection_id=connection_id,
            config=config,
            encrypted_credentials=encrypted_credentials,
            config_revision=1,
            identity=None,
            verification=VerificationVO(job_id=job_id, config_revision=1),
        )

    @classmethod
    def restore(
        cls,
        *,
        connection_id: EntityIdVO,
        config: ConnectionConfigVO,
        encrypted_credentials: bytes,
        config_revision: int,
        identity: ResourceIdentityVO | None,
        verification: VerificationVO,
    ) -> "Connection":
        """Проверяет согласованность восстановленного подключения."""
        connection = cls(
            id=connection_id,
            config=config,
            encrypted_credentials=encrypted_credentials,
            config_revision=config_revision,
            identity=identity,
            verification=verification,
        )
        connection.require_consistent_state()
        return connection

    def require_consistent_state(self) -> None:
        """Отклоняет несогласованные ревизии и результат без магазина."""
        if (
            not isinstance(self.id, EntityIdVO)
            or not isinstance(self.config, ConnectionConfigVO)
            or not isinstance(self.encrypted_credentials, bytes)
            or not self.encrypted_credentials
            or type(self.config_revision) is not int
            or self.config_revision < 1
            or not isinstance(self.verification, VerificationVO)
            or self.verification.config_revision != self.config_revision
        ):
            raise InvalidChannelStateError("Некорректное состояние подключения.")
        if self.identity is not None and not isinstance(
            self.identity, ResourceIdentityVO
        ):
            raise InvalidChannelStateError("Некорректная identity подключения.")
        if (
            self.verification.status is VerificationStatus.VERIFIED
            and self.identity is None
        ):
            raise InvalidChannelStateError(
                "Проверенное подключение требует identity магазина."
            )

    def change_settings(
        self,
        *,
        config: ConnectionConfigVO | None,
        encrypted_credentials: bytes | None,
        job_id: EntityIdVO,
    ) -> bool:
        """Атомарно меняет доступ и начинает проверку новой ревизии подключения."""
        if config is not None and not isinstance(config, ConnectionConfigVO):
            raise InvalidChannelStateError("Некорректная конфигурация подключения.")
        if encrypted_credentials is not None and (
            not isinstance(encrypted_credentials, bytes) or not encrypted_credentials
        ):
            raise InvalidChannelStateError(
                "Пустые credentials подключения недопустимы."
            )
        connection_changed = (
            config is not None and config != self.config
        ) or encrypted_credentials is not None
        if not connection_changed:
            return False
        next_revision = self.config_revision + 1
        verification = VerificationVO(job_id=job_id, config_revision=next_revision)
        self.config = config if config is not None else self.config
        self.encrypted_credentials = (
            encrypted_credentials
            if encrypted_credentials is not None
            else self.encrypted_credentials
        )
        self.config_revision = next_revision
        self.verification = verification
        return True

    def request_verification(self, *, job_id: EntityIdVO) -> None:
        """Начинает новое поколение проверки текущего доступа."""
        self.verification = VerificationVO(
            job_id=job_id, config_revision=self.config_revision
        )

    def accepts_result(self, *, job_id: EntityIdVO, config_revision: int) -> bool:
        """Принимает результат только для текущей ожидающей проверки."""
        return (
            self.config_revision == config_revision
            and self.verification.job_id == job_id
            and self.verification.status is VerificationStatus.PENDING
        )

    def can_confirm_identity(self, identity: ResourceIdentityVO) -> bool:
        """Разрешает первую identity либо повторное подтверждение того же магазина."""
        return self.identity is None or self.identity == identity

    def complete_verification(
        self,
        *,
        job_id: EntityIdVO,
        config_revision: int,
        identity: ResourceIdentityVO | None,
        error_code: str | None,
        now: datetime,
    ) -> bool:
        """Завершает актуальную проверку, сохраняя закреплённый магазин при отказе."""
        if not self.accepts_result(job_id=job_id, config_revision=config_revision):
            return False
        if identity is not None and not isinstance(identity, ResourceIdentityVO):
            raise InvalidResourceIdentityError("Некорректная identity результата.")
        if identity is not None and not self.can_confirm_identity(identity):
            error_code = "resource_identity_changed"
        if error_code is None and identity is None:
            raise InvalidResourceIdentityError("Проверка не определила магазин.")
        verification = VerificationVO(
            job_id=job_id,
            config_revision=config_revision,
            status=(
                VerificationStatus.VERIFIED
                if error_code is None
                else VerificationStatus.ERROR
            ),
            checked_at=now,
            error_code=error_code,
        )
        if error_code is None:
            self.identity = identity
        self.verification = verification
        return True
