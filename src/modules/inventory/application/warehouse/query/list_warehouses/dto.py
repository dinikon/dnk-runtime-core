from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class WarehouseListItemDTO:
    """Описывает строку списка без коллекций локаций и остатков."""

    id: UUID
    code: str
    name: str
    is_active: bool
    default_storage_location_id: UUID | None


@dataclass(frozen=True, slots=True)
class ListWarehousesResultDTO:
    """Передаёт страницу списка и общее число по тем же фильтрам."""

    items: tuple[WarehouseListItemDTO, ...]
    total: int
    offset: int
    limit: int
