from collections.abc import Mapping
from typing import Any
from src.modules.catalog.application.tag.query.get_tag.dto import GetTagDetailsDTO
from src.modules.catalog.application.tag.query.list_tags.dto import TagListItemDTO


class TagQueryMapper:
    """Создаёт собственные read DTO, не восстанавливая Domain."""

    @staticmethod
    def to_details(
        row: Mapping[str, Any], translations: dict[str, str], locale: str
    ) -> GetTagDetailsDTO:
        """Создаёт детали выбранной locale без fallback."""
        return GetTagDetailsDTO(
            row["id"], translations.get(locale), row["revision"], tuple(translations)
        )

    @staticmethod
    def to_list_item(row: Mapping[str, Any]) -> TagListItemDTO:
        """Создаёт строку конкретного списка справочника."""
        return TagListItemDTO(row["id"], row["label"], row["revision"])
