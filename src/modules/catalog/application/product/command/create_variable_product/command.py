from dataclasses import dataclass
from uuid import UUID

from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(frozen=True, slots=True)
class CreateVariableProductContent:
    locale: str
    name: str
    description: str | None = None


@dataclass(frozen=True, slots=True)
class CreateVariantSelection:
    attribute_id: UUID
    option_id: UUID


@dataclass(frozen=True, slots=True)
class CreateVariableVariant:
    sku_id: UUID
    selections: tuple[CreateVariantSelection, ...]


@dataclass(frozen=True, slots=True)
class CreateVariableProductCommand:
    actor_id: EntityIdVO
    variants: tuple[CreateVariableVariant, ...]
    contents: tuple[CreateVariableProductContent, ...] = ()
