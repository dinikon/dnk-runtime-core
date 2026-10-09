from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class GetWarehousePolicyDTO:
    """Настройки, принадлежащие контракту чтения карточки склада."""

    timezone: str


@dataclass(frozen=True, slots=True)
class GetWarehouseDetailsDTO:
    """Полная проекция карточки склада без поведения агрегата."""

    id: UUID
    code: str
    title: str
    type: str
    status: str
    policy: GetWarehousePolicyDTO
    revision: int
    created_at: datetime
    updated_at: datetime
    created_by: UUID
    updated_by: UUID
