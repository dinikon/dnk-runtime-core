from dataclasses import dataclass

from src.modules.catalog.domain.attribute.locale import AttributeLocaleVO
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(frozen=True, slots=True)
class GetAttributeQuery:
    attribute_id: EntityIdVO
    locale: AttributeLocaleVO
