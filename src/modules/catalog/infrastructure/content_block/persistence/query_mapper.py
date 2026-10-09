from collections.abc import Mapping
from typing import Any
from src.modules.catalog.application.content_block.query.get_content_block.dto import (
    GetContentBlockDetailsDTO,
)
from src.modules.catalog.application.content_block.query.list_content_blocks.dto import (
    ContentBlockListItemDTO,
)


class ContentBlockQueryMapper:
    """Создаёт DTO конкретного чтения без I/O и доменных объектов."""

    @staticmethod
    def to_details(row: Mapping[str, Any], locale: str) -> GetContentBlockDetailsDTO:
        """Преобразует карточку с явной locale без fallback."""
        return GetContentBlockDetailsDTO(
            id=row["id"],
            code=row["code"],
            is_system=row["is_system"],
            revision=row["revision"],
            label=row["translations"].get(locale),
            locales=tuple(row["translations"]),
            value_type=row["value_type"],
        )

    @staticmethod
    def to_list_item(row: Mapping[str, Any], locale: str) -> ContentBlockListItemDTO:
        """Преобразует отдельную строку списка в её собственный контракт."""
        return ContentBlockListItemDTO(
            id=row["id"],
            code=row["code"],
            is_system=row["is_system"],
            revision=row["revision"],
            label=row["translations"].get(locale),
            locales=tuple(row["translations"]),
            value_type=row["value_type"],
        )
