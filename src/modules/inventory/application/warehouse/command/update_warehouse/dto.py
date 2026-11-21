from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class UpdateWarehouseResultDTO:
    """Передаёт итог редактирования с сохранёнными ID и основной ссылкой."""

    id: UUID
    code: str
    name: str
    is_active: bool
    default_storage_location_id: UUID | None
