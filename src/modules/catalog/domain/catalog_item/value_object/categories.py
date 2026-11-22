from dataclasses import dataclass
from src.modules.catalog.domain.catalog_category.value_object.identifier import (
    CatalogCategoryIdVO,
)
from src.modules.catalog.domain.error import InvalidCatalogValueError


@dataclass(frozen=True, slots=True)
class CatalogItemCategoriesVO:
    """Основная и дополнительные категории одной корневой карточки."""

    primary_category_id: CatalogCategoryIdVO
    additional_category_ids: tuple[CatalogCategoryIdVO, ...] = ()

    def __post_init__(self) -> None:
        """Проверяет обязательную основную категорию и уникальность выбранных ссылок."""
        if not isinstance(self.additional_category_ids, tuple):
            raise InvalidCatalogValueError(
                "Некорректный список дополнительных категорий.", ("categories",)
            )
        identifiers = (self.primary_category_id, *self.additional_category_ids)
        if not all(isinstance(value, CatalogCategoryIdVO) for value in identifiers):
            raise InvalidCatalogValueError(
                "Укажите идентификаторы категорий.", ("categories",)
            )
        if len(set(identifiers)) != len(identifiers):
            raise InvalidCatalogValueError(
                "Категория повторяется в назначениях.", ("categories",)
            )

    def with_primary(
        self, identifier: CatalogCategoryIdVO
    ) -> "CatalogItemCategoriesVO":
        """Переводит прежнюю основную в дополнительные при продвижении выбранной."""
        if identifier == self.primary_category_id:
            return self
        additional = tuple(
            value for value in self.additional_category_ids if value != identifier
        )
        if identifier in self.additional_category_ids:
            additional += (self.primary_category_id,)
        return CatalogItemCategoriesVO(identifier, additional)
