from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID
from enum import StrEnum

from src.modules.channels.domain.channel.value_object.connection_config import (
    ConnectionConfigVO,
)
from src.modules.channels.domain.content_delivery.value_object import (
    DeliveryContextVO,
    DeliveryFieldIssueVO,
)
from src.modules.channels.application.content_media.contracts import MediaFile


class ContentWriteOutcome(StrEnum):
    """Отделяет безопасный отказ до записи от возможного внешнего изменения."""

    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    UNKNOWN = "unknown"
    PARTIAL = "partial"


@dataclass(frozen=True, slots=True)
class PreparedContentRequest:
    """Версионированный запрос пакета; bytes могут содержать секретные media URL."""

    schema: str
    payload: bytes = field(repr=False)
    content_hash: str


@dataclass(frozen=True, slots=True)
class ContentMediaResult:
    """Подтверждённое соответствие конкретного локального media."""

    media_id: UUID
    remote_id: str


@dataclass(frozen=True, slots=True)
class ContentMediaChecksum:
    """Контрольная сумма исходного файла для доказуемой сверки новой загрузки."""

    media_id: UUID
    sha256: str


@dataclass(frozen=True, slots=True)
class ContentMediaSource:
    """Owned-файл сохранённой попытки; storage читается после закрытия UoW."""

    media_id: UUID
    file: MediaFile = field(repr=False)


@dataclass(frozen=True, slots=True)
class ContentDeliveryResult:
    """Безопасный результат внешнего шага без полного ответа WooCommerce."""

    outcome: ContentWriteOutcome
    fields: tuple[str, ...] = ()
    media: tuple[ContentMediaResult, ...] = ()
    error_code: str | None = None
    issues: tuple[DeliveryFieldIssueVO, ...] = ()


@dataclass(frozen=True, slots=True)
class ContentReconciliationResult:
    """Результат только чтения: неподтверждённая запись остаётся неоднозначной."""

    confirmed: bool
    fields: tuple[str, ...] = ()
    media: tuple[ContentMediaResult, ...] = ()
    error_code: str | None = None
    issues: tuple[DeliveryFieldIssueVO, ...] = ()

    @property
    def outcome(self) -> ContentWriteOutcome:
        """Несовпадение при чтении не доказывает безопасный отказ прежней записи."""
        return (
            ContentWriteOutcome.CONFIRMED
            if self.confirmed
            else ContentWriteOutcome.UNKNOWN
        )


@dataclass(frozen=True, slots=True)
class ContentWorkSnapshot:
    """Неизменяемый сетевой шаг после commit подготовки."""

    representation_id: UUID
    publication_id: UUID
    job_id: UUID
    platform_kind: str
    generation: int
    context: DeliveryContextVO
    config: ConnectionConfigVO
    encrypted_credentials: bytes = field(repr=False)
    request: PreparedContentRequest
    reconcile: bool
    known_media: tuple[ContentMediaResult, ...] = ()
    media_sources: tuple[ContentMediaSource, ...] = field(default=(), repr=False)


@dataclass(frozen=True, slots=True)
class ContentDeliveryRow:
    """Публичная проекция состояния одной цели без расшифровки запроса."""

    publication_id: UUID
    external_id: str
    role: str
    publication_kind: str
    revision: int
    requested_generation: int
    sending_generation: int | None
    applied_generation: int | None
    status: str
    confirmed_fields: tuple[str, ...]
    error_code: str | None
    updated_at: datetime
    completed_at: datetime | None
    content_fingerprint: str
    current_job_id: UUID
    recovery_required: bool = False
    field_issues: tuple[DeliveryFieldIssueVO, ...] = ()
    initial_error_code: str | None = None
    last_success_at: datetime | None = None
    applied_content_fingerprint: str | None = None
