from dataclasses import dataclass

from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(slots=True, frozen=True)
class ListContactsQuery:
    """Параметры поиска и offset-пагинации контактов."""

    tenant_id: EntityIdVO
    q: str = ""
    limit: int = 25
    offset: int = 0


__all__ = ["ListContactsQuery"]
