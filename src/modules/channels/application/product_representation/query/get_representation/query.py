from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class GetRepresentationQuery:
    """Запрашивает сохранённые overrides без создания записи при чтении."""

    channel_id: UUID
    group_id: UUID
