from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class GetPublicationQuery:
    """Запрашивает одну публикацию и подпись выбранной позиции."""

    publication_id: UUID
    locale: str = "uk"
