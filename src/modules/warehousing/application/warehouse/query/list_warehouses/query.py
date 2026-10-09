from dataclasses import dataclass

from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(frozen=True, slots=True)
class ListWarehousesQuery:
    """Фильтры и cursor-пагинация списка складов текущего tenant."""

    tenant_id: EntityIdVO
    status: str | None = None
    warehouse_type: str | None = None
    cursor: str | None = None
    limit: int = 50
