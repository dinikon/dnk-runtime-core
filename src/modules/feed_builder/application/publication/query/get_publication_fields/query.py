from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class GetPublicationFieldsQuery:
    """Определяет публикацию, поля которой нужно показать в редакторе."""

    feed_id: UUID
    publication_id: UUID
