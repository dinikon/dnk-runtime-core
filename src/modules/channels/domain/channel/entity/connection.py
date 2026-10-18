from dataclasses import dataclass, field
from typing import Self
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.channels.domain.channel.value_object.settings import (
    ConnectionSettingsVO,
)
from src.modules.channels.domain.error import (
    ChannelsConflictError,
    ChannelsValidationError,
)


@dataclass(slots=True)
class Connection:
    """Единственное техническое подключение, принадлежащее Channel."""

    id: EntityIdVO
    settings: ConnectionSettingsVO
    credentials_ciphertext: str = field(repr=False)
    candidate_ciphertext: str | None = field(repr=False)
    resource_identity: str | None
    verification_status: str
    verification_job_id: EntityIdVO | None
    generation: int
    is_paused: bool
    reason_code: str | None
    scope_limitations: tuple[str, ...]

    @classmethod
    def create(
        cls, identifier: EntityIdVO, settings: ConnectionSettingsVO, ciphertext: str
    ) -> Self:
        """Создаёт непроверенное подключение с защищённым кандидатом credentials."""
        return cls.restore(
            identifier,
            settings,
            "",
            ciphertext,
            None,
            "unverified",
            None,
            0,
            False,
            None,
            (),
        )

    @classmethod
    def restore(
        cls,
        identifier: EntityIdVO,
        settings: ConnectionSettingsVO,
        credentials_ciphertext: str,
        candidate_ciphertext: str | None,
        resource_identity: str | None,
        verification_status: str,
        verification_job_id: EntityIdVO | None,
        generation: int,
        is_paused: bool,
        reason_code: str | None,
        scope_limitations: tuple[str, ...],
    ) -> Self:
        """Восстанавливает сущность без нового задания проверки."""
        if not isinstance(identifier, EntityIdVO) or (
            verification_job_id is not None
            and not isinstance(verification_job_id, EntityIdVO)
        ):
            raise ChannelsValidationError("invalid_connection_identifier")
        if generation < 0 or verification_status not in (
            "unverified",
            "queued",
            "verified",
            "error",
        ):
            raise ChannelsValidationError("invalid_connection_state")
        if verification_status == "verified" and (
            not resource_identity or not credentials_ciphertext
        ):
            raise ChannelsValidationError("invalid_verified_connection")
        return cls(
            identifier,
            settings,
            credentials_ciphertext,
            candidate_ciphertext,
            resource_identity,
            verification_status,
            verification_job_id,
            generation,
            is_paused,
            reason_code,
            scope_limitations,
        )

    def request_verification(self, job_id: EntityIdVO) -> None:
        """Меняет generation и закрепляет единственное актуальное задание проверки."""
        self.generation += 1
        self.verification_job_id = job_id
        self.verification_status = "queued"
        self.reason_code = None

    def change_settings(
        self, settings: ConnectionSettingsVO, ciphertext: str | None
    ) -> None:
        """Сохраняет кандидата без замены проверенных ключей и identity."""
        if self.resource_identity and settings.endpoint != self.settings.endpoint:
            raise ChannelsConflictError("resource_change_requires_new_channel")
        self.settings = settings
        self.generation += 1
        self.verification_status = "unverified"
        self.verification_job_id = None
        self.reason_code = None
        if ciphertext is not None:
            self.candidate_ciphertext = ciphertext

    def apply_verification(
        self, identity: str | None, reason: str | None, limitations: tuple[str, ...]
    ) -> None:
        """Подтверждает ресурс либо сохраняет безопасный код отказа."""
        if not identity or len(identity) > 1000:
            identity, reason = (None, reason or "resource_identity_unavailable")
        if identity and self.resource_identity and (self.resource_identity != identity):
            identity, reason = (None, "resource_identity_changed")
        if identity is None:
            self.verification_status, self.reason_code = (
                "error",
                reason or "verification_failed",
            )
            return
        self.resource_identity = identity
        if self.candidate_ciphertext:
            self.credentials_ciphertext = self.candidate_ciphertext
            self.candidate_ciphertext = None
        self.verification_status, self.reason_code = ("verified", None)
        self.scope_limitations = limitations

    def pause(self) -> None:
        """Останавливает сетевые шаги и делает старые результаты неактуальными."""
        self.is_paused = True
        self.generation += 1
        if self.verification_status == "queued":
            self.verification_status = "unverified"

    def resume(self) -> None:
        """Снимает техническую паузу без включения исходящей синхронизации."""
        self.is_paused = False
