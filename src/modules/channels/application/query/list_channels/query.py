from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ListChannelsQuery:
    tenant_id: UUID
