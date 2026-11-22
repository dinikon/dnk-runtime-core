from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ListFeedsQuery:
    """Передаёт поиск и страницу; отсутствие статуса исключает архивные записи."""

    search: str | None = None
    status: str | None = None
    limit: int = 50
    offset: int = 0
