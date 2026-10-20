from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ContentUpdateSummaryDTO:
    """Передаёт строку истории с итогом и числом публикаций."""

    id: UUID
    status: str
    created_at: datetime
    total: int


@dataclass(frozen=True, slots=True)
class ListContentUpdatesResultDTO:
    """Возвращает последние операции без тяжёлых снимков описаний."""

    items: tuple[ContentUpdateSummaryDTO, ...]
