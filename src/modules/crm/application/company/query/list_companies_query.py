from dataclasses import dataclass

from src.modules.shared import EntityIdVO


@dataclass(slots=True, frozen=True)
class ListCompaniesQuery:
    """Query application-слоя на получение страницы компаний."""

    tenant_id: EntityIdVO
    limit: int = 50
    offset: int = 0
