from dataclasses import dataclass

from src.modules.inventory.domain.category.error import InvalidCategoryNameError


@dataclass(slots=True, frozen=True)
class CategoryNameVO:
    """Value object названия категории товаров."""

    value: str

    def __post_init__(self) -> None:
        """Нормализует и проверяет непустое название категории."""
        if not isinstance(self.value, str):
            raise InvalidCategoryNameError()
        normalized = self.value.strip()
        if not normalized:
            raise InvalidCategoryNameError()
        object.__setattr__(self, "value", normalized)
