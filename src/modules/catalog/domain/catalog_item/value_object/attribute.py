from dataclasses import dataclass
from src.modules.catalog.domain.attribute.value_object.identifier import AttributeIdVO
from src.modules.catalog.domain.attribute.value_object.option_id import (
    AttributeOptionIdVO,
)
from src.modules.catalog.domain.catalog_item.value_object.override import OverrideMode
from src.modules.catalog.domain.error import InvalidCatalogValueError


@dataclass(frozen=True, slots=True)
class EnumAttributeAssignmentVO:
    """Собственный набор enum-options либо явная очистка характеристики."""

    attribute_id: AttributeIdVO
    option_ids: tuple[AttributeOptionIdVO, ...]
    visible: bool
    position: int
    mode: OverrideMode = OverrideMode.SET

    def __post_init__(self) -> None:
        """Проверяет собственные значения; оси и принадлежность проверяет агрегат."""
        if (
            self.mode == OverrideMode.INHERIT
            or self.position < 0
            or type(self.visible) is not bool
            or len(set(self.option_ids)) != len(self.option_ids)
        ):
            raise InvalidCatalogValueError("Некорректное назначение атрибута.")
        if (self.mode == OverrideMode.SET) != bool(self.option_ids):
            raise InvalidCatalogValueError(
                "Set требует options, clear не содержит options."
            )
