from dataclasses import dataclass

from src.modules.catalog.domain.category.value_object.identifier import CategoryIdVO
from src.modules.catalog.domain.category.value_object.locale import CategoryLocaleVO


@dataclass(frozen=True)
class GetCategoryQuery:
    category_id: CategoryIdVO
    locale: CategoryLocaleVO
