from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ListChannelsQuery:
    """Передаёт параметры на чтение списка каналов текущего tenant."""

    tenant_id: UUID
