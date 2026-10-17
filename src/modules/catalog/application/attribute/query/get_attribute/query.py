from dataclasses import dataclass
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.catalog.domain.attribute.value_object.identifier import AttributeIdVO


@dataclass(frozen=True, slots=True)
class GetAttributeQuery:
    """Явное чтение get_attribute в доверенном tenant."""

    tenant_id: EntityIdVO
    attribute_id: AttributeIdVO
    locale: str
