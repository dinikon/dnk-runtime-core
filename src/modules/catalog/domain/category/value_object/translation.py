from dataclasses import dataclass

from src.modules.catalog.domain.category.error import InvalidCategoryError
from src.modules.catalog.domain.category.value_object.locale import CategoryLocaleVO


@dataclass(frozen=True, slots=True)
class CategoryTranslationVO:
    locale: CategoryLocaleVO
    name: str

    def __post_init__(self) -> None:
        if not isinstance(self.locale, CategoryLocaleVO) or not isinstance(
            self.name, str
        ):
            raise InvalidCategoryError("Category translation is invalid.")
        name = self.name.strip()
        if not 1 <= len(name) <= 255:
            raise InvalidCategoryError("Category name must contain 1-255 characters.")
        object.__setattr__(self, "name", name)
