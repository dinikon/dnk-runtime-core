from dataclasses import dataclass
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.catalog.domain.content_block.value_object.identifier import (
    ContentBlockIdVO,
)


@dataclass(frozen=True, slots=True)
class DeleteContentBlockCommand:
    """Вход сценария delete_content_block; контекст получен от доверенной границы."""

    tenant_id: EntityIdVO
    actor_id: EntityIdVO
    content_block_id: ContentBlockIdVO
    expected_revision: int
