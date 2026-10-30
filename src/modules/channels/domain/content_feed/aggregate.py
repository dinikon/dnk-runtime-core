from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta
from src.modules.channels.domain.content_feed.delivery import (
    FeedDeliveryVO,
    FeedDeliveryPhase,
    FeedImportContextVO,
    FeedImportReportVO,
    FeedPublicationVerificationVO,
)

from src.modules.channels.domain.content_feed.error import ContentFeedError
from src.modules.channels.domain.content_feed.value_object import FeedSourceVO
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(slots=True)
class ContentFeed:
    """Владеет источником, разрешением и отзывным доступом постоянного фида."""

    id: EntityIdVO
    connection_id: EntityIdVO
    scope_key: str
    revision: int
    enabled: bool
    source: FeedSourceVO
    source_url_encrypted: bytes = field(repr=False)
    access_token_hash: bytes | None = field(repr=False)
    access_token_encrypted: bytes | None = field(repr=False)
    created_at: datetime
    updated_at: datetime
    created_by: EntityIdVO
    updated_by: EntityIdVO
    delivery: FeedDeliveryVO = field(default_factory=FeedDeliveryVO)
    delivery_request_encrypted: bytes | None = field(default=None, repr=False)

    @classmethod
    def create(
        cls,
        *,
        identifier: EntityIdVO,
        connection_id: EntityIdVO,
        source: FeedSourceVO,
        source_url_encrypted: bytes,
        token_hash: bytes,
        token_encrypted: bytes,
        actor: EntityIdVO,
        now: datetime,
    ) -> "ContentFeed":
        """Создаёт выключенный фид полного каталога с первой ревизией."""
        return cls.restore(
            identifier=identifier,
            connection_id=connection_id,
            scope_key="catalog",
            revision=1,
            enabled=False,
            source=source,
            source_url_encrypted=source_url_encrypted,
            access_token_hash=token_hash,
            access_token_encrypted=token_encrypted,
            created_at=now,
            updated_at=now,
            created_by=actor,
            updated_by=actor,
        )

    @classmethod
    def restore(
        cls,
        *,
        identifier: EntityIdVO,
        connection_id: EntityIdVO,
        scope_key: str,
        revision: int,
        enabled: bool,
        source: FeedSourceVO,
        source_url_encrypted: bytes,
        access_token_hash: bytes | None,
        access_token_encrypted: bytes | None,
        created_at: datetime,
        updated_at: datetime,
        created_by: EntityIdVO,
        updated_by: EntityIdVO,
        delivery: FeedDeliveryVO | None = None,
        delivery_request_encrypted: bytes | None = None,
    ) -> "ContentFeed":
        """Отклоняет повреждённые состояния без автоматического исправления."""
        delivery = delivery if delivery is not None else FeedDeliveryVO()
        if (
            not isinstance(delivery, FeedDeliveryVO)
            or (delivery.context is not None and not delivery_request_encrypted)
            or (
                delivery.phase == FeedDeliveryPhase.IDLE
                and delivery_request_encrypted is not None
            )
        ):
            raise ContentFeedError("feed_delivery_invalid")
        if (
            not all(
                isinstance(v, EntityIdVO)
                for v in (identifier, connection_id, created_by, updated_by)
            )
            or scope_key != "catalog"
            or type(revision) is not int
            or revision < 1
            or type(enabled) is not bool
            or not isinstance(source, FeedSourceVO)
            or not isinstance(source_url_encrypted, bytes)
            or not source_url_encrypted
            or (access_token_hash is None) != (access_token_encrypted is None)
            or (
                access_token_hash is not None
                and (
                    not isinstance(access_token_hash, bytes)
                    or len(access_token_hash) != 32
                    or not isinstance(access_token_encrypted, bytes)
                    or not access_token_encrypted
                )
            )
            or (enabled and access_token_hash is None)
        ):
            raise ContentFeedError("feed_state_invalid")
        if (
            any(
                not isinstance(v, datetime) or v.tzinfo is None or v.utcoffset() is None
                for v in (created_at, updated_at)
            )
            or updated_at < created_at
        ):
            raise ContentFeedError("feed_audit_invalid")
        return cls(
            identifier,
            connection_id,
            scope_key,
            revision,
            enabled,
            source,
            source_url_encrypted,
            access_token_hash,
            access_token_encrypted,
            created_at,
            updated_at,
            created_by,
            updated_by,
            delivery,
            delivery_request_encrypted,
        )

    def require_revision(self, expected_revision: int) -> None:
        """Проверяет версию до любой операции, включая сохранение без изменений."""
        if type(expected_revision) is not int or expected_revision != self.revision:
            raise ContentFeedError("feed_revision_conflict", conflict=True)

    def change_source(
        self,
        *,
        source: FeedSourceVO,
        encrypted_url: bytes,
        expected_revision: int,
        actor: EntityIdVO,
        now: datetime,
    ) -> None:
        """Замена источника аннулирует разрешение выдачи."""
        self.require_revision(expected_revision)
        if self.source != source or self.source_url_encrypted != encrypted_url:
            self.require_delivery_finished()
            self._change(
                source=source,
                encrypted_url=encrypted_url,
                enabled=False,
                token_hash=self.access_token_hash,
                token_encrypted=self.access_token_encrypted,
                actor=actor,
                now=now,
            )

    def enable(
        self,
        *,
        expected_revision: int,
        blockers: tuple[str, ...],
        actor: EntityIdVO,
        now: datetime,
    ) -> None:
        """Разрешает выдачу только после полной проверки текущего документа."""
        self.require_revision(expected_revision)
        if blockers:
            raise ContentFeedError(blockers[0])
        if self.access_token_hash is None:
            raise ContentFeedError("feed_access_revoked")
        if not self.enabled:
            self._change(
                source=self.source,
                encrypted_url=self.source_url_encrypted,
                enabled=True,
                token_hash=self.access_token_hash,
                token_encrypted=self.access_token_encrypted,
                actor=actor,
                now=now,
            )

    def disable(
        self, *, expected_revision: int, actor: EntityIdVO, now: datetime
    ) -> None:
        """Идемпотентно выключает endpoint с сохранением токена."""
        self.require_revision(expected_revision)
        if self.enabled:
            self._change(
                source=self.source,
                encrypted_url=self.source_url_encrypted,
                enabled=False,
                token_hash=self.access_token_hash,
                token_encrypted=self.access_token_encrypted,
                actor=actor,
                now=now,
            )

    def rotate_access_token(
        self,
        *,
        token_hash: bytes,
        token_encrypted: bytes,
        expected_revision: int,
        actor: EntityIdVO,
        now: datetime,
    ) -> None:
        """Немедленно заменяет доступ, не включая ранее выключенный фид."""
        self.require_revision(expected_revision)
        self._change(
            source=self.source,
            encrypted_url=self.source_url_encrypted,
            enabled=self.enabled,
            token_hash=token_hash,
            token_encrypted=token_encrypted,
            actor=actor,
            now=now,
        )

    def revoke_access(
        self, *, expected_revision: int, actor: EntityIdVO, now: datetime
    ) -> None:
        """Отзывает ссылку и выключает фид одним переходом."""
        self.require_revision(expected_revision)
        if self.access_token_hash is not None:
            self._change(
                source=self.source,
                encrypted_url=self.source_url_encrypted,
                enabled=False,
                token_hash=None,
                token_encrypted=None,
                actor=actor,
                now=now,
            )

    def _change(
        self,
        *,
        source: FeedSourceVO,
        encrypted_url: bytes,
        enabled: bool,
        token_hash: bytes | None,
        token_encrypted: bytes | None,
        actor: EntityIdVO,
        now: datetime,
    ) -> None:
        """Проверяет весь кандидат до изменения состояния и единственного шага ревизии."""
        candidate = self.restore(
            identifier=self.id,
            connection_id=self.connection_id,
            scope_key=self.scope_key,
            revision=self.revision + 1,
            enabled=enabled,
            source=source,
            source_url_encrypted=encrypted_url,
            access_token_hash=token_hash,
            access_token_encrypted=token_encrypted,
            created_at=self.created_at,
            updated_at=now,
            created_by=self.created_by,
            updated_by=actor,
            delivery=self.delivery,
            delivery_request_encrypted=self.delivery_request_encrypted,
        )
        self.source, self.source_url_encrypted = (
            candidate.source,
            candidate.source_url_encrypted,
        )
        self.enabled = candidate.enabled
        self.access_token_hash = candidate.access_token_hash
        self.access_token_encrypted = candidate.access_token_encrypted
        self.revision, self.updated_at, self.updated_by = (
            candidate.revision,
            candidate.updated_at,
            candidate.updated_by,
        )

    def require_delivery_finished(self) -> None:
        """Блокирует замену источника и удаление во время неразрешённого импорта."""
        if self.delivery.busy:
            raise ContentFeedError("feed_import_active", conflict=True)

    def request_import(
        self,
        *,
        operation_id: EntityIdVO,
        actor_id: EntityIdVO,
        job_id: EntityIdVO,
        expected_revision: int,
        expected_delivery_revision: int,
        force_update: bool,
        now: datetime,
    ) -> bool:
        """Создаёт одно намерение и возвращает существующее при повторе request_id."""
        self.require_revision(expected_revision)
        if self.delivery.operation_id == operation_id:
            if (
                self.delivery.actor_id != actor_id
                or self.delivery.force_update != force_update
            ):
                raise ContentFeedError("feed_import_request_conflict", conflict=True)
            return False
        self.delivery.require_revision(expected_delivery_revision)
        self.require_delivery_finished()
        if not self.enabled or self.access_token_hash is None:
            raise ContentFeedError("feed_import_disabled")
        self._set_delivery(
            FeedDeliveryVO(
                revision=self.delivery.revision + 1,
                phase=FeedDeliveryPhase.QUEUED,
                operation_id=operation_id,
                actor_id=actor_id,
                current_job_id=job_id,
                force_update=force_update,
                requested_at=now,
                tracking_deadline=now + timedelta(hours=1),
            ),
            encrypted_request=None,
        )
        return True

    def begin_submission(
        self, *, context: FeedImportContextVO, encrypted_request: bytes, now: datetime
    ) -> None:
        """Сохраняет submitting до единственного внешнего POST."""
        if (
            self.delivery.phase != FeedDeliveryPhase.QUEUED
            or not self.enabled
            or context.feed_revision != self.revision
        ):
            raise ContentFeedError("feed_delivery_state_conflict", conflict=True)
        self._set_delivery(
            replace(
                self.delivery,
                revision=self.delivery.revision + 1,
                phase=FeedDeliveryPhase.SUBMITTING,
                context=context,
                submission_started_at=now,
                last_checked_at=now,
            ),
            encrypted_request=encrypted_request,
        )

    def record_acceptance(
        self,
        *,
        external_id: str,
        job_id: EntityIdVO,
        now: datetime,
        manual: bool = False,
    ) -> None:
        """Закрепляет ID до polling; ручная привязка остаётся явно отмеченной."""
        allowed = (
            {FeedDeliveryPhase.UNKNOWN, FeedDeliveryPhase.NEEDS_ATTENTION}
            if manual
            else {FeedDeliveryPhase.SUBMITTING}
        )
        if self.delivery.phase not in allowed or self.delivery.context is None:
            raise ContentFeedError("feed_delivery_state_conflict", conflict=True)
        self._set_delivery(
            replace(
                self.delivery,
                revision=self.delivery.revision + 1,
                phase=FeedDeliveryPhase.PROCESSING,
                external_import_id=external_id,
                current_job_id=job_id,
                last_checked_at=now,
                error_code=None,
                manual_resolution="import_id_attached" if manual else None,
            )
        )

    def record_submission_failure(
        self, *, code: str, uncertain: bool, now: datetime
    ) -> None:
        """Не даёт Shared Jobs повторить неоднозначно принятый POST."""
        if (
            self.delivery.phase
            not in {FeedDeliveryPhase.QUEUED, FeedDeliveryPhase.SUBMITTING}
            or uncertain
            and self.delivery.phase != FeedDeliveryPhase.SUBMITTING
        ):
            raise ContentFeedError("feed_delivery_state_conflict", conflict=True)
        phase = FeedDeliveryPhase.UNKNOWN if uncertain else FeedDeliveryPhase.FAILED
        self._set_delivery(
            replace(
                self.delivery,
                revision=self.delivery.revision + 1,
                phase=phase,
                last_checked_at=now,
                finished_at=None if uncertain else now,
                error_code=code,
            )
        )

    def record_report(
        self, *, report: FeedImportReportVO, job_id: EntityIdVO, now: datetime
    ) -> None:
        """Отчёт провайдера запускает отдельную проверку применения."""
        if self.delivery.phase != FeedDeliveryPhase.PROCESSING:
            raise ContentFeedError("feed_delivery_state_conflict", conflict=True)
        self._set_delivery(
            replace(
                self.delivery,
                revision=self.delivery.revision + 1,
                phase=FeedDeliveryPhase.VERIFYING,
                report=report,
                current_job_id=job_id,
                last_checked_at=now,
                error_code=None,
            )
        )

    def wait_for_report(
        self, *, job_id: EntityIdVO, now: datetime, code: str | None
    ) -> None:
        """Переносит только чтение известного импорта, сохраняя общий deadline."""
        if self.delivery.phase != FeedDeliveryPhase.PROCESSING:
            raise ContentFeedError("feed_delivery_state_conflict", conflict=True)
        self._set_delivery(
            replace(
                self.delivery,
                revision=self.delivery.revision + 1,
                current_job_id=job_id,
                last_checked_at=now,
                error_code=code,
            )
        )

    def require_attention(self, *, code: str, now: datetime) -> None:
        """Приостанавливает работу, не объявляя внешний импорт отменённым или неуспешным."""
        self._set_delivery(
            replace(
                self.delivery,
                revision=self.delivery.revision + 1,
                phase=FeedDeliveryPhase.NEEDS_ATTENTION,
                error_code=code,
                last_checked_at=now,
            )
        )

    def record_verification(
        self,
        *,
        results: tuple[FeedPublicationVerificationVO, ...],
        now: datetime,
        code: str | None,
    ) -> None:
        """Завершает сценарий с отдельными доказательствами по полям."""
        self._set_delivery(
            self.delivery.with_verification(
                verification=results, now=now, error_code=code
            )
        )

    def resume_import(
        self, *, job_id: EntityIdVO, actor_id: EntityIdVO, now: datetime
    ) -> None:
        """Восстанавливает queued либо чтение известного ID; submitting не отправляется повторно."""
        if self.delivery.phase not in {
            FeedDeliveryPhase.QUEUED,
            FeedDeliveryPhase.PROCESSING,
            FeedDeliveryPhase.VERIFYING,
            FeedDeliveryPhase.NEEDS_ATTENTION,
        }:
            raise ContentFeedError("feed_import_resume_forbidden", conflict=True)
        phase = self.delivery.phase
        if phase == FeedDeliveryPhase.NEEDS_ATTENTION:
            if self.delivery.external_import_id is None:
                raise ContentFeedError("feed_import_id_required", conflict=True)
            phase = (
                FeedDeliveryPhase.VERIFYING
                if self.delivery.report is not None
                else FeedDeliveryPhase.PROCESSING
            )
        self._set_delivery(
            replace(
                self.delivery,
                revision=self.delivery.revision + 1,
                phase=phase,
                current_job_id=job_id,
                actor_id=actor_id,
                error_code=None,
                tracking_deadline=now + timedelta(hours=1),
                last_checked_at=now,
            )
        )

    def resolve_unknown_import(self, *, actor_id: EntityIdVO, now: datetime) -> None:
        """Фиксирует ручное подтверждение отсутствия импорта без нового POST."""
        if (
            self.delivery.phase
            not in {FeedDeliveryPhase.UNKNOWN, FeedDeliveryPhase.NEEDS_ATTENTION}
            or self.delivery.external_import_id is not None
        ):
            raise ContentFeedError("feed_import_resolution_forbidden", conflict=True)
        self._set_delivery(
            replace(
                self.delivery,
                revision=self.delivery.revision + 1,
                phase=FeedDeliveryPhase.RESOLVED,
                actor_id=actor_id,
                finished_at=now,
                manual_resolution="confirmed_not_submitted",
                error_code=None,
            )
        )

    def _set_delivery(
        self, value: FeedDeliveryVO, *, encrypted_request: bytes | None = None
    ) -> None:
        """Проверяет кандидат до записи; прогресс не меняет настройки и владельца доступа."""
        encrypted = (
            encrypted_request
            if encrypted_request is not None
            else self.delivery_request_encrypted
        )
        if value.phase == FeedDeliveryPhase.QUEUED:
            encrypted = None
        if value.context is not None and not encrypted:
            raise ContentFeedError("feed_delivery_invalid")
        self.delivery, self.delivery_request_encrypted = value, encrypted
