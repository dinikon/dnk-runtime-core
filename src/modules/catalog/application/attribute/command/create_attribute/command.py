from dataclasses import dataclass
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.catalog.application.attribute.option_input import AttributeOptionInput


@dataclass(frozen=True, slots=True)
class CreateAttributeCommand:
    """Вход сценария create_attribute с доверенным контекстом."""

    tenant_id: EntityIdVO
    actor_id: EntityIdVO
    code: str
    locale: str
    label: str
    options: tuple[AttributeOptionInput, ...] = ()
