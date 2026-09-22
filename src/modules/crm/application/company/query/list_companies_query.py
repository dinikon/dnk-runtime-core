from dataclasses import dataclass

from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(slots=True, frozen=True)
class ListCompaniesQuery:
    """Параметры поиска и offset-пагинации компаний."""

    tenant_id: EntityIdVO
    q: str = ""
    limit: int = 25
    offset: int = 0


__all__ = ["ListCompaniesQuery"]
