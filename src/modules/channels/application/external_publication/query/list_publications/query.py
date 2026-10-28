"""Параметры чтения карточек из локального снимка."""

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ListPublicationsQuery:
    """Передаёт выбранный канал и параметры отображения."""

    channel_id: UUID
    search: str = ""
    offset: int = 0
    limit: int = 25
    locale: str | None = None
