from collections.abc import Mapping
from typing import Any
from src.modules.catalog.application.product_type.query.get_product_type.dto import (
    GetProductTypeDetailsDTO,
    GetProductTypeBlockDTO,
)
from src.modules.catalog.application.product_type.query.list_product_types.dto import (
    ProductTypeListItemDTO,
    ProductTypeListBlockDTO,
)


class ProductTypeQueryMapper:
    """Создаёт DTO конкретного чтения без I/O и доменных объектов."""

    @staticmethod
    def to_details(
        row: Mapping[str, Any], locale: str, blocks: tuple[Mapping[str, Any], ...]
    ) -> GetProductTypeDetailsDTO:
        """Преобразует карточку с явной locale без fallback."""
        return GetProductTypeDetailsDTO(
            id=row["id"],
            code=row["code"],
            is_system=row["is_system"],
            revision=row["revision"],
            label=row["translations"].get(locale),
            locales=tuple(row["translations"]),
            schema_version=row["schema_version"],
            blocks=tuple(
                GetProductTypeBlockDTO(
                    block_id=b["block_id"],
                    code=b["code"],
                    value_type=b["value_type"],
                    label=b["label"],
                    scope=b["scope"],
                    required=b["required"],
                    position=b["position"],
                )
                for b in blocks
            ),
        )

    @staticmethod
    def to_list_item(
        row: Mapping[str, Any], locale: str, blocks: tuple[Mapping[str, Any], ...]
    ) -> ProductTypeListItemDTO:
        """Преобразует отдельную строку списка в её собственный контракт."""
        return ProductTypeListItemDTO(
            id=row["id"],
            code=row["code"],
            is_system=row["is_system"],
            revision=row["revision"],
            label=row["translations"].get(locale),
            locales=tuple(row["translations"]),
            schema_version=row["schema_version"],
            blocks=tuple(
                ProductTypeListBlockDTO(
                    block_id=b["block_id"],
                    code=b["code"],
                    value_type=b["value_type"],
                    label=b["label"],
                    scope=b["scope"],
                    required=b["required"],
                    position=b["position"],
                )
                for b in blocks
            ),
        )
