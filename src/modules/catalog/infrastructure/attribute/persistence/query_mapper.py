from collections.abc import Mapping, Sequence
from typing import Any
from src.modules.catalog.application.attribute.query.get_attribute.dto import (
    GetAttributeDetailsDTO,
    AttributeOptionDetailsDTO,
)
from src.modules.catalog.application.attribute.query.list_attributes.dto import (
    AttributeListItemDTO,
)


class AttributeQueryMapper:
    """Создаёт отдельные read DTO без Domain-фабрик и I/O."""

    @staticmethod
    def to_details(
        row: Mapping[str, Any],
        translations: dict[str, str],
        options: Sequence[Mapping[str, Any]],
        locale: str,
    ) -> GetAttributeDetailsDTO:
        """Преобразует определение и options с явной locale без fallback."""
        return GetAttributeDetailsDTO(
            row["id"],
            row["code"],
            "enum",
            translations.get(locale),
            row["revision"],
            tuple(translations),
            tuple(
                AttributeOptionDetailsDTO(
                    o["id"],
                    o["code"],
                    o["translations"].get(locale),
                    o["position"],
                    tuple(o["translations"]),
                )
                for o in options
            ),
        )

    @staticmethod
    def to_list_item(row: Mapping[str, Any]) -> AttributeListItemDTO:
        """Создаёт собственную строку списка определений."""
        return AttributeListItemDTO(
            row["id"], row["code"], row["label"], row["revision"], row["option_count"]
        )
