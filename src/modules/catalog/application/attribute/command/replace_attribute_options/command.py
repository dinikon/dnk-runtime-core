from dataclasses import dataclass
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.catalog.domain.attribute.value_object.identifier import AttributeIdVO
from src.modules.catalog.application.attribute.option_input import AttributeOptionInput


@dataclass(frozen=True, slots=True)
class ReplaceAttributeOptionsCommand:
    """Вход сценария replace_attribute_options с доверенным контекстом."""

    tenant_id: EntityIdVO
    actor_id: EntityIdVO
    attribute_id: AttributeIdVO
    expected_revision: int
    locale: str
    options: tuple[AttributeOptionInput, ...]
