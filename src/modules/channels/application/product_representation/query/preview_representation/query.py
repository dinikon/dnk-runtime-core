from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class PreviewRepresentationQuery:
    """Запрашивает текущее представление существующей группы без записи и отправки."""

    channel_id: UUID
    group_id: UUID
    locales: tuple[str, ...] | None = None
