from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class StartContentUpdateCommand:
    """Передаёт одно идемпотентное намерение подготовить сравнение."""

    tenant_id: UUID
    actor_id: UUID
    channel_id: UUID
    run_id: UUID
    publication_ids: tuple[UUID, ...]
