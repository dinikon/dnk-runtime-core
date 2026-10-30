from dataclasses import dataclass, field
from hashlib import sha256
from uuid import UUID

from src.modules.channels.application.content_feed.contracts import FeedSnapshot
from src.modules.channels.domain.channel.value_object.connection_config import (
    ConnectionConfigVO,
)
from src.modules.channels.domain.content_feed.delivery import (
    FeedDeliveryVO,
    FeedImportContextVO,
    FeedImportReportVO,
)


def feed_content_fingerprint(snapshot: FeedSnapshot) -> str:
    """Хеширует детерминированный типизированный снимок без URL, секретов и времени."""
    return sha256(repr(snapshot).encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class FeedSubmissionResult:
    """Принятие POST не означает завершение или применение импорта."""

    outcome: str
    external_id: str | None = None
    error_code: str | None = None


@dataclass(frozen=True, slots=True)
class FeedPollResult:
    """Отсутствие распознанного отчёта не превращается в успешное завершение."""

    report: FeedImportReportVO | None = None
    error_code: str | None = None
    blocked: bool = False


@dataclass(frozen=True, slots=True)
class FeedImportStep:
    """Неизменяемый снимок одного внешнего шага между короткими UoW."""

    feed_id: UUID
    channel_id: UUID
    operation_id: UUID
    job_id: UUID
    actor_id: UUID
    phase: str
    config: ConnectionConfigVO
    connection_revision: int
    identity_namespace: str
    identity_key: str
    encrypted_credentials: bytes = field(repr=False)
    encrypted_request: bytes | None = field(repr=False)
    external_id: str | None
    feed_revision: int
    force_update: bool


@dataclass(frozen=True, slots=True)
class PreparedFeedImport:
    """Нативный документ пакета и публичный контекст до submitting."""

    payload: bytes = field(repr=False)
    context: FeedImportContextVO


@dataclass(frozen=True, slots=True)
class FeedImportDetails:
    """Публичное состояние последней операции без подготовленного запроса."""

    state: FeedDeliveryVO
    recovery_required: bool
    can_start: bool
    can_resume: bool
    can_attach: bool
    can_resolve: bool
