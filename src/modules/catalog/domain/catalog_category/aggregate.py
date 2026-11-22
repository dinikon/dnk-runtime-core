from dataclasses import dataclass
from typing import Self, Mapping
from src.modules.catalog.domain.catalog_category.value_object.identifier import (
    CatalogCategoryIdVO,
)
from src.modules.catalog.domain.catalog_category.entity.translation import (
    CatalogCategoryTranslation,
)
from src.modules.catalog.domain.value_object.locale import LocaleVO
from src.modules.catalog.domain.error import (
    CatalogConflictError,
    CatalogNotFoundError,
    InvalidCatalogValueError,
)


@dataclass(slots=True)
class CatalogCategory:
    """Узел дерева со своими названиями на языках каталога."""

    id: CatalogCategoryIdVO
    parent_id: CatalogCategoryIdVO | None
    source_locale: LocaleVO
    translations: dict[str, CatalogCategoryTranslation]
    is_default: bool

    @classmethod
    def create(
        cls,
        identifier: CatalogCategoryIdVO,
        parent_id: CatalogCategoryIdVO | None,
        source_locale: LocaleVO,
        name: str,
    ) -> Self:
        """Создаёт категорию с названием на исходном языке."""
        return cls.restore(
            identifier, parent_id, source_locale, {source_locale.value: name}
        )

    @classmethod
    def restore(
        cls,
        identifier: CatalogCategoryIdVO,
        parent_id: CatalogCategoryIdVO | None,
        source_locale: LocaleVO,
        names: Mapping[str, str],
        *,
        is_default: bool = False,
    ) -> Self:
        """Восстанавливает узел и проверяет наличие исходного перевода."""
        if source_locale.value not in names:
            raise InvalidCatalogValueError("Укажите название на исходном языке.")
        if identifier == parent_id:
            raise InvalidCatalogValueError(
                "Категория не может быть собственным родителем."
            )
        return cls(
            identifier,
            parent_id,
            source_locale,
            {
                code: CatalogCategoryTranslation.restore(LocaleVO(code), name)
                for code, name in names.items()
            },
            is_default=is_default,
        )

    def translate(self, locale: LocaleVO, name: str) -> None:
        """Добавляет или заменяет название указанной локали."""
        self.translations[locale.value] = CatalogCategoryTranslation.create(
            locale, name
        )

    def move(
        self,
        parent_id: CatalogCategoryIdVO | None,
        parents: Mapping[CatalogCategoryIdVO, CatalogCategoryIdVO | None],
    ) -> None:
        """Проверяет цепочку предков и меняет положение узла."""
        seen = {self.id}
        ancestor = parent_id
        while ancestor is not None:
            if ancestor in seen:
                raise CatalogConflictError("Перенос создаст цикл в дереве категорий.")
            if ancestor not in parents:
                raise CatalogNotFoundError("Родительская категория отсутствует.")
            seen.add(ancestor)
            ancestor = parents[ancestor]
        self.parent_id = parent_id

    def ensure_removable(self, *, has_children: bool, has_items: bool) -> None:
        """Проверяет ссылки товаров, дочерних узлов и назначение по умолчанию."""
        if self.is_default:
            raise CatalogConflictError(
                "Сначала выберите другую категорию по умолчанию."
            )
        if has_children or has_items:
            raise CatalogConflictError("Сначала перенесите подкатегории и товары.")
