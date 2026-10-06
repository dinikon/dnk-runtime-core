from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class GetChannelQuery:
    """Передаёт параметры на чтение карточки канала текущего tenant."""

    tenant_id: UUID
    channel_id: UUID
