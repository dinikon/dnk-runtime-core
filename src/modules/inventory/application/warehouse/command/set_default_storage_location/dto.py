from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class SetDefaultStorageLocationResultDTO:
    """Возвращает карточку склада после назначения основной STORAGE-локации."""

    id: UUID
    code: str
    name: str
    is_active: bool
    default_storage_location_id: UUID
