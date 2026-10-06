from dataclasses import dataclass
from uuid import UUID

from src.modules.catalog.application.product.command.create_product.command import (
    CreateProductContent,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(frozen=True, slots=True)
class CreateVariableProductCommand:
    actor_id: EntityIdVO
    sku_ids: tuple[UUID, ...]
    contents: tuple[CreateProductContent, ...] = ()
