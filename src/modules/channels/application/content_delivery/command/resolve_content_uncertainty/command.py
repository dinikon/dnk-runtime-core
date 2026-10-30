from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ResolveContentUncertaintyCommand:
    """Явное решение завершить неподтверждённую попытку без внешней записи."""

    tenant_id: UUID
    actor_id: UUID
    channel_id: UUID
    group_id: UUID
    publication_id: UUID
    expected_revision: int
    acknowledge_unconfirmed: bool
