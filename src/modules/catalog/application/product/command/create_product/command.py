from dataclasses import dataclass
from uuid import UUID

from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(frozen=True, slots=True)
class CreateProductContent:
    locale: str
    blocks: dict[str, str]


@dataclass(frozen=True, slots=True)
class CreateProductCommand:
    actor_id: EntityIdVO
    sku_id: UUID
    contents: tuple[CreateProductContent, ...] = ()
    product_type_id: UUID | None = None
    schema_version: int | None = None
