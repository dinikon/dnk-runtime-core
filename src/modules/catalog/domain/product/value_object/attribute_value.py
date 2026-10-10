from dataclasses import dataclass
from src.modules.catalog.domain.attribute.value_object.identifier import AttributeIdVO
from src.modules.catalog.domain.attribute.value_object.option_id import (
    AttributeOptionIdVO,
)
from src.modules.catalog.domain.error import InvalidCatalogValueError


@dataclass(frozen=True, slots=True)
class ProductAttributeValueVO:
    """Одно общее enum-значение; видимость независима от участия в вариациях."""

    attribute_id: AttributeIdVO
    option_id: AttributeOptionIdVO
    visible: bool
    position: int

    def __post_init__(self) -> None:
        """Проверяет типы и локальный диапазон порядка."""
        if (
            not isinstance(self.attribute_id, AttributeIdVO)
            or not isinstance(self.option_id, AttributeOptionIdVO)
            or not isinstance(self.visible, bool)
            or isinstance(self.position, bool)
            or not isinstance(self.position, int)
            or self.position < 0
        ):
            raise InvalidCatalogValueError("Некорректное общее enum-значение.")
