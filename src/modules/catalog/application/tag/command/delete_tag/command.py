from dataclasses import dataclass
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.catalog.domain.tag.value_object.identifier import TagIdVO


@dataclass(frozen=True, slots=True)
class DeleteTagCommand:
    """Вход сценария delete_tag с доверенным контекстом."""

    tenant_id: EntityIdVO
    actor_id: EntityIdVO
    tag_id: TagIdVO
    expected_revision: int
