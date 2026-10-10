from dataclasses import dataclass
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(frozen=True, slots=True)
class ListAttributesQuery:
    """Явное чтение list_attributes в доверенном tenant."""

    tenant_id: EntityIdVO
    locale: str
    search: str = ""
    page: int = 1
    page_size: int = 20
