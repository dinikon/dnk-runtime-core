from dataclasses import dataclass
from uuid import UUID

from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(frozen=True)
class CreateCategoryTranslation:
    locale: str
    name: str


@dataclass(frozen=True)
class CreateCategoryCommand:
    tenant_id: EntityIdVO
    actor_id: EntityIdVO
    parent_id: UUID | None
    translations: tuple[CreateCategoryTranslation, ...]
