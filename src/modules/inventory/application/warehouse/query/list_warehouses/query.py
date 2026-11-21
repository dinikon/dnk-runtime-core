from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ListWarehousesQuery:
    """Задаёт страницу, поиск по коду/названию и фильтр активности."""

    offset: int = 0
    limit: int = 50
    search: str | None = None
    is_active: bool | None = None
