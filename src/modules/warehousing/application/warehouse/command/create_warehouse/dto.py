from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CreateWarehouseResultDTO:
    """Результат создания склада; успешный commit выполняется внешним UoW."""

    id: UUID
    code: str
    status: str
    revision: int
