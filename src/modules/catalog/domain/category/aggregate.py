from dataclasses import dataclass, field
from datetime import datetime
from types import MappingProxyType
from typing import Mapping, Self

from src.modules.catalog.domain.category.error import InvalidCategoryError
from src.modules.catalog.domain.category.value_object.identifier import CategoryIdVO
from src.modules.catalog.domain.category.value_object.translation import (
    CategoryTranslationVO,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(eq=False)
class Category:
    """Самостоятельный корень дерева категорий."""

    id: CategoryIdVO
    parent_id: CategoryIdVO | None
    created_at: datetime
    updated_at: datetime
    created_by: EntityIdVO
    updated_by: EntityIdVO
    _translations: dict[str, CategoryTranslationVO] = field(
        default_factory=dict, repr=False
    )

    @property
    def translations(self) -> Mapping[str, CategoryTranslationVO]:
        return MappingProxyType(self._translations)

    @classmethod
    def create(
        cls,
        *,
        category_id: CategoryIdVO,
        parent_id: CategoryIdVO | None,
        translations: tuple[CategoryTranslationVO, ...],
        actor_id: EntityIdVO,
        now: datetime,
    ) -> Self:
        if not translations:
            raise InvalidCategoryError("Category requires at least one translation.")
        by_locale: dict[str, CategoryTranslationVO] = {}
        for translation in translations:
            if not isinstance(translation, CategoryTranslationVO):
                raise InvalidCategoryError("Category translation is invalid.")
            code = translation.locale.value
            if code in by_locale:
                raise InvalidCategoryError("Duplicate category translation locale.")
            by_locale[code] = translation
        if parent_id == category_id:
            raise InvalidCategoryError("Category cannot be its own parent.")
        return cls(category_id, parent_id, now, now, actor_id, actor_id, by_locale)

    def set_translation(
        self, translation: CategoryTranslationVO, *, actor_id: EntityIdVO, now: datetime
    ) -> None:
        if not isinstance(translation, CategoryTranslationVO):
            raise InvalidCategoryError("Category translation is invalid.")
        self._translations[translation.locale.value] = translation
        self.updated_at = now
        self.updated_by = actor_id

    def move_to(
        self, parent_id: CategoryIdVO | None, *, actor_id: EntityIdVO, now: datetime
    ) -> None:
        if parent_id == self.id:
            raise InvalidCategoryError("Category cannot be its own parent.")
        self.parent_id = parent_id
        self.updated_at = now
        self.updated_by = actor_id
