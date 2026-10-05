from dataclasses import dataclass
from uuid import UUID

from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(frozen=True, slots=True)
class CreateProductContent:
    locale: str
    name: str
    description: str | None = None


@dataclass(frozen=True, slots=True)
class CreateProductCommand:
    actor_id: EntityIdVO
    sku_id: UUID
    contents: tuple[CreateProductContent, ...] = ()
