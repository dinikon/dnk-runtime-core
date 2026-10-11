from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class RequestTrashEmptyResultDTO:
    """Возвращает ID durable прохода и границу файлов без обещания физического удаления."""

    job_id: UUID
    cutoff: datetime
