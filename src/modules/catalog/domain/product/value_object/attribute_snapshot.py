from dataclasses import dataclass
from src.modules.catalog.domain.attribute.value_object.identifier import AttributeIdVO
from src.modules.catalog.domain.attribute.value_object.option_id import (
    AttributeOptionIdVO,
)


@dataclass(frozen=True, slots=True)
class EnumAttributeSnapshot:
    """Минимальный снимок enum-определения для проверки осей и общих значений Product."""

    id: AttributeIdVO
    option_ids: frozenset[AttributeOptionIdVO]
