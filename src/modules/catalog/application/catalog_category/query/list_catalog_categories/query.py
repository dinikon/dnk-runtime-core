from dataclasses import dataclass
from src.modules.catalog.domain.value_object.locale import LocaleVO


@dataclass(frozen=True, slots=True)
class ListCatalogCategoriesQuery:
    """Язык отображения дерева категорий."""

    locale: LocaleVO
