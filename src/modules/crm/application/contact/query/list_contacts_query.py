from dataclasses import dataclass

from src.modules.shared import EntityIdVO


@dataclass(slots=True, frozen=True)
class ListContactsQuery:
    """Query application-слоя на список контактов tenant с пагинацией."""

    tenant_id: EntityIdVO
    limit: int
    offset: int
