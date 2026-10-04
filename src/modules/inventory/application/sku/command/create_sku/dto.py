from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CreateSkuResultDTO:
    """Данные SKU без доменных сущностей и инфраструктурных типов."""

    id: UUID
    code: str
    title: str
    created_at: datetime
    updated_at: datetime
    created_by: UUID
    updated_by: UUID
