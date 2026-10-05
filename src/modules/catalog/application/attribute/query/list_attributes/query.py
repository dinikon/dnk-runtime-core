from dataclasses import dataclass

from src.modules.catalog.domain.attribute.locale import AttributeLocaleVO


@dataclass(frozen=True, slots=True)
class ListAttributesQuery:
    locale: AttributeLocaleVO
