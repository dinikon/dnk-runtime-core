from dataclasses import dataclass
from uuid import UUID


@dataclass(slots=True, frozen=True)
class ListContactsQuery:
    tenant_id: UUID
    limit: int
    offset: int
