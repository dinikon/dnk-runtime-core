from dataclasses import dataclass, replace
from datetime import datetime
from enum import StrEnum

from src.modules.channels.domain.content_feed.error import ContentFeedError
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class FeedDeliveryPhase(StrEnum):
    """Различает передачу ссылки, обработку и проверку фактического контента."""

    IDLE = "idle"
    QUEUED = "queued"
    SUBMITTING = "submitting"
    PROCESSING = "processing"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    FAILED = "failed"
    UNKNOWN = "unknown"
    NEEDS_ATTENTION = "needs_attention"
    RESOLVED = "resolved"


@dataclass(frozen=True, slots=True)
class FeedImportContextVO:
    """Закрепляет настройки и identity магазина без credentials и ссылки фида."""

    feed_revision: int
    connection_revision: int
    identity_namespace: str
    identity_key: str
    content_fingerprint: str

    def __post_init__(self) -> None:
        """Проверяет полноту подготовленного контекста."""
        if (
            type(self.feed_revision) is not int
            or self.feed_revision < 1
            or type(self.connection_revision) is not int
            or self.connection_revision < 1
            or not self.identity_namespace
            or not self.identity_key
            or len(self.content_fingerprint) != 64
        ):
            raise ContentFeedError("feed_import_context_invalid")


@dataclass(frozen=True, slots=True)
class FeedImportIssueVO:
    """Безопасная причина отчёта; свободный текст и URL провайдера не сохраняются."""

    code: str
    stage: str


@dataclass(frozen=True, slots=True)
class FeedImportReportVO:
    """Хранит документированные счётчики, сохраняя отсутствие значения."""

    status: str
    total: int | None = None
    updated: int | None = None
    created: int | None = None
    imported: int | None = None
    not_changed: int | None = None
    not_in_file: int | None = None
    with_errors_count: int | None = None
    issues: tuple[FeedImportIssueVO, ...] = ()

    def __post_init__(self) -> None:
        """Не приравнивает отсутствующие или противоречивые счётчики к нулю."""
        if self.status not in {"SUCCESS", "PARTIAL", "FATAL"} or any(
            value is not None and (type(value) is not int or value < 0)
            for value in (
                self.total,
                self.updated,
                self.created,
                self.imported,
                self.not_changed,
                self.not_in_file,
                self.with_errors_count,
            )
        ):
            raise ContentFeedError("feed_import_report_invalid")


@dataclass(frozen=True, slots=True)
class FeedFieldVerificationVO:
    """Отдельное доказательство применения поля, а не общий статус HTTP-запроса."""

    field: str
    locale: str | None
    status: str

    def __post_init__(self) -> None:
        """Ограничивает публичные статусы проверки."""
        if self.field not in {"title", "body", "gallery"} or self.status not in {
            "confirmed",
            "mismatch",
            "unconfirmed",
            "obsolete",
        }:
            raise ContentFeedError("feed_verification_invalid")


@dataclass(frozen=True, slots=True)
class FeedPublicationVerificationVO:
    """Проверенный результат одной существующей публикации."""

    publication_id: EntityIdVO
    external_id: str
    import_key: str
    fields: tuple[FeedFieldVerificationVO, ...]
    observed_gallery: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class FeedDeliveryVO:
    """Состояние последней операции, принадлежащее ContentFeed, со своей ревизией."""

    revision: int = 0
    phase: FeedDeliveryPhase = FeedDeliveryPhase.IDLE
    operation_id: EntityIdVO | None = None
    actor_id: EntityIdVO | None = None
    current_job_id: EntityIdVO | None = None
    force_update: bool = False
    context: FeedImportContextVO | None = None
    external_import_id: str | None = None
    report: FeedImportReportVO | None = None
    verification: tuple[FeedPublicationVerificationVO, ...] = ()
    requested_at: datetime | None = None
    submission_started_at: datetime | None = None
    last_checked_at: datetime | None = None
    finished_at: datetime | None = None
    tracking_deadline: datetime | None = None
    error_code: str | None = None
    manual_resolution: str | None = None

    def __post_init__(self) -> None:
        """Отклоняет противоречия до изменения агрегата или восстановления из SQL."""
        if (
            type(self.revision) is not int
            or self.revision < 0
            or not isinstance(self.phase, FeedDeliveryPhase)
            or type(self.force_update) is not bool
        ):
            raise ContentFeedError("feed_delivery_invalid")
        if self.phase == FeedDeliveryPhase.IDLE:
            if (
                self.revision
                or self.force_update
                or self.verification
                or any(
                    v is not None
                    for v in (
                        self.operation_id,
                        self.actor_id,
                        self.current_job_id,
                        self.context,
                        self.external_import_id,
                        self.report,
                        self.requested_at,
                        self.submission_started_at,
                        self.last_checked_at,
                        self.finished_at,
                        self.tracking_deadline,
                        self.error_code,
                        self.manual_resolution,
                    )
                )
            ):
                raise ContentFeedError("feed_delivery_invalid")
            return
        if (
            self.revision < 1
            or not all(
                isinstance(v, EntityIdVO)
                for v in (self.operation_id, self.actor_id, self.current_job_id)
            )
            or self.requested_at is None
            or self.tracking_deadline is None
        ):
            raise ContentFeedError("feed_delivery_invalid")
        dates = (
            self.requested_at,
            self.submission_started_at,
            self.last_checked_at,
            self.finished_at,
            self.tracking_deadline,
        )
        if (
            any(
                v is not None
                and (
                    not isinstance(v, datetime)
                    or v.tzinfo is None
                    or v.utcoffset() is None
                    or v < self.requested_at
                )
                for v in dates
            )
            or self.tracking_deadline < self.requested_at
        ):
            raise ContentFeedError("feed_delivery_invalid")
        if (
            self.phase
            in {
                FeedDeliveryPhase.SUBMITTING,
                FeedDeliveryPhase.PROCESSING,
                FeedDeliveryPhase.VERIFYING,
                FeedDeliveryPhase.COMPLETED,
            }
            and self.context is None
        ):
            raise ContentFeedError("feed_delivery_invalid")
        if self.external_import_id is not None and (
            not isinstance(self.external_import_id, str)
            or not self.external_import_id.strip()
            or len(self.external_import_id) > 128
        ):
            raise ContentFeedError("feed_import_id_invalid")
        if (
            self.phase
            in {
                FeedDeliveryPhase.PROCESSING,
                FeedDeliveryPhase.VERIFYING,
                FeedDeliveryPhase.COMPLETED,
            }
            and self.external_import_id is None
        ):
            raise ContentFeedError("feed_delivery_invalid")
        if (
            self.phase in {FeedDeliveryPhase.VERIFYING, FeedDeliveryPhase.COMPLETED}
            and self.report is None
        ):
            raise ContentFeedError("feed_delivery_invalid")
        if (
            self.context is not None
            and not isinstance(self.context, FeedImportContextVO)
            or self.report is not None
            and not isinstance(self.report, FeedImportReportVO)
        ):
            raise ContentFeedError("feed_delivery_invalid")
        if self.phase == FeedDeliveryPhase.QUEUED and any(
            v is not None
            for v in (
                self.context,
                self.external_import_id,
                self.report,
                self.submission_started_at,
            )
        ):
            raise ContentFeedError("feed_delivery_invalid")
        if self.phase in {FeedDeliveryPhase.SUBMITTING, FeedDeliveryPhase.UNKNOWN} and (
            self.context is None or self.submission_started_at is None
        ):
            raise ContentFeedError("feed_delivery_invalid")

    @property
    def busy(self) -> bool:
        """Не разрешает новый POST до разрешения неопределённой или активной операции."""
        return self.phase in {
            FeedDeliveryPhase.QUEUED,
            FeedDeliveryPhase.SUBMITTING,
            FeedDeliveryPhase.PROCESSING,
            FeedDeliveryPhase.VERIFYING,
            FeedDeliveryPhase.UNKNOWN,
            FeedDeliveryPhase.NEEDS_ATTENTION,
        }

    def require_revision(self, expected_revision: int) -> None:
        """Защищает отдельный счётчик прогресса от устаревшего запроса."""
        if type(expected_revision) is not int or expected_revision != self.revision:
            raise ContentFeedError("feed_delivery_revision_conflict", conflict=True)

    def with_verification(
        self,
        *,
        verification: tuple[FeedPublicationVerificationVO, ...],
        now: datetime,
        error_code: str | None,
    ) -> "FeedDeliveryVO":
        """Завершает проверку без утверждения, что весь контент применён."""
        if self.phase != FeedDeliveryPhase.VERIFYING:
            raise ContentFeedError("feed_delivery_state_conflict", conflict=True)
        return replace(
            self,
            revision=self.revision + 1,
            phase=FeedDeliveryPhase.COMPLETED,
            verification=verification,
            finished_at=now,
            last_checked_at=now,
            error_code=error_code,
        )
