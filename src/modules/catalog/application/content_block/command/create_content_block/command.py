from src.modules.catalog.domain.content_block.value_object.value_type import (
    ContentValueType,
)
from dataclasses import dataclass
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(frozen=True, slots=True)
class CreateContentBlockCommand:
    """Вход сценария create_content_block; контекст получен от доверенной границы."""

    tenant_id: EntityIdVO
    actor_id: EntityIdVO
    code: str
    locale: str
    label: str
    value_type: ContentValueType
