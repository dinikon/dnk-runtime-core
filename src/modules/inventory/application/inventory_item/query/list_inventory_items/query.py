from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ListInventoryItemsQuery:
    """Задаёт страницу списка и необязательный поиск по SKU текущего tenant."""

    offset: int = 0
    limit: int = 50
    search: str | None = None
