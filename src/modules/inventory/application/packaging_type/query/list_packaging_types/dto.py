from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class PackagingTypeListItemDTO:
    """Передаёт строку списка форм-факторов тары."""

    id: UUID
    code: str
    name: str
    is_active: bool


@dataclass(frozen=True, slots=True)
class ListPackagingTypesResultDTO:
    """Передаёт страницу и общее число по тем же фильтрам."""

    items: tuple[PackagingTypeListItemDTO, ...]
    total: int
    offset: int
    limit: int
