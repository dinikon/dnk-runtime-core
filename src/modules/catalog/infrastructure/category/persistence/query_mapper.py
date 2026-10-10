from collections.abc import Mapping
from typing import Any
from src.modules.catalog.application.category.query.get_category.dto import (
    GetCategoryDetailsDTO,
)
from src.modules.catalog.application.category.query.list_categories.dto import (
    CategoryListItemDTO,
)


class CategoryQueryMapper:
    """Создаёт собственные read DTO, не восстанавливая Domain."""

    @staticmethod
    def to_details(
        row: Mapping[str, Any], translations: dict[str, str], locale: str
    ) -> GetCategoryDetailsDTO:
        """Создаёт детали выбранной locale без fallback."""
        return GetCategoryDetailsDTO(
            row["id"],
            translations.get(locale),
            row["revision"],
            tuple(translations),
            row["parent_id"],
            row["child_count"],
        )

    @staticmethod
    def to_list_item(row: Mapping[str, Any]) -> CategoryListItemDTO:
        """Создаёт строку конкретного списка справочника."""
        return CategoryListItemDTO(
            row["id"],
            row["label"],
            row["revision"],
            row["parent_id"],
            row["child_count"],
        )
