from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CreatedVariableSelectionDTO:
    attribute_id: UUID
    option_id: UUID


@dataclass(frozen=True, slots=True)
class CreatedVariableVariantDTO:
    id: UUID
    sku_id: UUID
    sku_code: str
    selections: tuple[CreatedVariableSelectionDTO, ...]


@dataclass(frozen=True, slots=True)
class CreateVariableProductResultDTO:
    id: UUID
    type: str
    variants: tuple[CreatedVariableVariantDTO, ...]
    content_locales: tuple[str, ...]
    created_at: datetime
    updated_at: datetime
    created_by: UUID
    updated_by: UUID
