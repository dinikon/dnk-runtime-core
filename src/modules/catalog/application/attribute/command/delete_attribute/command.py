from dataclasses import dataclass
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.catalog.domain.attribute.value_object.identifier import AttributeIdVO


@dataclass(frozen=True, slots=True)
class DeleteAttributeCommand:
    """Вход сценария delete_attribute с доверенным контекстом."""

    tenant_id: EntityIdVO
    actor_id: EntityIdVO
    attribute_id: AttributeIdVO
    expected_revision: int
