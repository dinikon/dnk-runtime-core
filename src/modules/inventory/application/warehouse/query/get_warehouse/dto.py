from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class GetWarehouseResultDTO:
    """Передаёт результат сценария склада без объектов хранения."""

    id: UUID
    code: str
    name: str
    is_active: bool
    default_storage_location_id: UUID | None
