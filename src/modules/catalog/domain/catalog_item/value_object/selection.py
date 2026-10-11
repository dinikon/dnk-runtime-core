from dataclasses import dataclass
from src.modules.catalog.domain.attribute.value_object.identifier import AttributeIdVO
from src.modules.catalog.domain.attribute.value_object.option_id import (
    AttributeOptionIdVO,
)
from src.modules.catalog.domain.error import InvalidCatalogValueError


@dataclass(frozen=True, slots=True)
class VariationSelectionVO:
    """Неизменяемый набор выбранных attribute/option ID."""

    values: tuple[tuple[AttributeIdVO, AttributeOptionIdVO], ...] = ()

    def __post_init__(self) -> None:
        """Запрещает повтор attribute и нормализует порядок для сравнения."""
        if any(
            not isinstance(a, AttributeIdVO) or not isinstance(o, AttributeOptionIdVO)
            for a, o in self.values
        ):
            raise InvalidCatalogValueError(
                "Selection содержит некорректные идентичности."
            )
        if len({a for a, o in self.values}) != len(self.values):
            raise InvalidCatalogValueError("Selection повторяет характеристику.")
        object.__setattr__(
            self, "values", tuple(sorted(self.values, key=lambda item: str(item[0])))
        )
