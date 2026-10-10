from dataclasses import dataclass
from src.modules.catalog.domain.attribute.value_object.identifier import AttributeIdVO
from src.modules.catalog.domain.attribute.value_object.option_id import (
    AttributeOptionIdVO,
)
from src.modules.catalog.domain.error import InvalidCatalogValueError


@dataclass(frozen=True, slots=True)
class VariationAxis:
    """Ось выбора с устойчивыми ID и явным порядком."""

    attribute_id: AttributeIdVO
    option_ids: tuple[AttributeOptionIdVO, ...]
    position: int

    def __post_init__(self) -> None:
        """Проверяет собственные значения оси, не структуру Product."""
        if not isinstance(self.attribute_id, AttributeIdVO) or any(
            not isinstance(o, AttributeOptionIdVO) for o in self.option_ids
        ):
            raise InvalidCatalogValueError("Ось содержит некорректные идентичности.")
        if (
            not self.option_ids
            or len(set(self.option_ids)) != len(self.option_ids)
            or self.position < 0
        ):
            raise InvalidCatalogValueError(
                "Ось требует уникальные options и неотрицательный порядок."
            )
