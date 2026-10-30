from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class GetContentDeliveriesQuery:
    """Параметры чтения результатов группы в текущем tenant."""

    tenant_id: UUID
    channel_id: UUID
    group_id: UUID
