from datetime import datetime
from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CleanupExpiredTrashCandidateDTO:
    """Проекция идентификатора кандидата до повторной проверки под write lock."""

    file_id: UUID


@dataclass(frozen=True, slots=True)
class CleanupExpiredTrashResultDTO:
    """Итог постановки заданий и курсор следующей порции, без обещания commit."""

    queued_count: int
    requeued_count: int
    next_after_id: UUID | None


@dataclass(frozen=True, slots=True)
class CleanupExpiredTrashBacklogDTO:
    """Снимок просроченной корзины и ожидающих удаления файлов для worker-метрик."""

    expired_count: int
    expired_size_bytes: int
    oldest_purge_after: datetime | None
    pending_count: int
    pending_size_bytes: int
