from dataclasses import dataclass

from src.modules.catalog.domain.category.value_object.locale import CategoryLocaleVO


@dataclass(frozen=True)
class ListCategoriesQuery:
    locale: CategoryLocaleVO
