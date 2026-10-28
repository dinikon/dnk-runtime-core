"""Параметры чтения карточек из локального снимка."""

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class GetPublicationQuery:
    """Передаёт выбранный канал и параметры отображения."""

    channel_id: UUID
    publication_id: UUID
    locale: str | None = None
