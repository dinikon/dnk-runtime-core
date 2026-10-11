from dataclasses import dataclass
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(frozen=True, slots=True)
class GetDefaultProductTypeQuery:
    """Запрос фиксированной схемы Default."""

    tenant_id: EntityIdVO
    locale: str
