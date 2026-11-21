from dataclasses import dataclass
from datetime import date
from uuid import UUID


@dataclass(frozen=True, slots=True)
class GetStockLotResultDTO:
    """Передаёт результат сценария партии без ORM или HTTP-схем."""

    id: UUID
    inventory_item_id: UUID
    number: str
    manufactured_on: date | None
    expires_on: date | None
