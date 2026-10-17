from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class EmptyTrashCandidateDTO:
    """Проекция ID файла текущей порции до блокировки и повторной проверки состояния."""

    file_id: UUID


@dataclass(frozen=True, slots=True)
class EmptyTrashResultDTO:
    """Сообщает число поставленных удалений и курсор продолжения прохода корзины."""

    queued_count: int
    next_after_id: UUID | None
