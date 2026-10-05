from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CreatedAttributeOptionDTO:
    id: UUID
    code: str


@dataclass(frozen=True, slots=True)
class CreateAttributeResultDTO:
    id: UUID
    code: str
    options: tuple[CreatedAttributeOptionDTO, ...]
    created_at: datetime
    updated_at: datetime
    created_by: UUID
    updated_by: UUID
