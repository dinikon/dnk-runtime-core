from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ListPackagingTypesQuery:
    """Передаёт параметры страницы и необязательные фильтры типов тары."""

    offset: int = 0
    limit: int = 50
    search: str | None = None
    is_active: bool | None = None
