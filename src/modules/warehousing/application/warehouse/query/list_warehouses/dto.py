from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ListWarehouseItemDTO:
    """Строка списка складов, принадлежащая только этому сценарию."""

    id: UUID
    code: str
    title: str
    type: str
    status: str
    revision: int


@dataclass(frozen=True, slots=True)
class ListWarehousesResultDTO:
    """Страница списка с курсором следующей страницы либо None."""

    items: tuple[ListWarehouseItemDTO, ...]
    next_cursor: str | None
