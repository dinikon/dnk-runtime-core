from dataclasses import dataclass
from src.modules.catalog.domain.attribute.value_object.identifier import AttributeIdVO
from src.modules.catalog.domain.attribute.value_object.option_id import (
    AttributeOptionIdVO,
)
from src.modules.catalog.domain.error import InvalidCatalogValueError


@dataclass(frozen=True, slots=True)
class EnumAttributeAssignmentVO:
    """Непустой набор enum-options характеристики товара."""

    attribute_id: AttributeIdVO
    option_ids: tuple[AttributeOptionIdVO, ...]
    visible: bool
    position: int

    def __post_init__(self) -> None:
        """Проверяет собственные значения; принадлежность проверяет агрегат."""
        if (
            type(self.position) is not int
            or self.position < 0
            or type(self.visible) is not bool
            or len(set(self.option_ids)) != len(self.option_ids)
        ):
            raise InvalidCatalogValueError("Некорректное назначение атрибута.")
        if not self.option_ids:
            raise InvalidCatalogValueError(
                "Характеристика требует непустой набор options."
            )
