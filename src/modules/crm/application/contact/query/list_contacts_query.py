from dataclasses import dataclass

from src.modules.shared import EntityIdVO


@dataclass(slots=True, frozen=True)
class ListContactsQuery:
    tenant_id: EntityIdVO
    limit: int
    offset: int
