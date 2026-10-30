from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID
from enum import StrEnum

from src.modules.channels.domain.channel.value_object.connection_config import (
    ConnectionConfigVO,
)
from src.modules.channels.domain.content_delivery.value_object import DeliveryContextVO


class ContentWriteOutcome(StrEnum):
    """Отделяет безопасный отказ до записи от возможного внешнего изменения."""

    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    UNKNOWN = "unknown"


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
class ContentDeliveryResult:
    """Безопасный результат внешнего шага без полного ответа WooCommerce."""

    outcome: ContentWriteOutcome
    fields: tuple[str, ...] = ()
    media: tuple[ContentMediaResult, ...] = ()
    error_code: str | None = None


@dataclass(frozen=True, slots=True)
class ContentReconciliationResult:
    """Результат только чтения: неподтверждённая запись остаётся неоднозначной."""

    confirmed: bool
    fields: tuple[str, ...] = ()
    media: tuple[ContentMediaResult, ...] = ()
    error_code: str | None = None

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
