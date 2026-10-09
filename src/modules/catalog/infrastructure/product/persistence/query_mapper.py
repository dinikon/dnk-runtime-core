from collections.abc import Mapping
from typing import Any
from src.modules.catalog.application.product.query.get_product.dto import (
    GetProductDetailsDTO,
)
from src.modules.catalog.application.product.query.list_products.dto import (
    ProductListItemDTO,
)
from src.modules.catalog.application.product.query.get_variant.dto import (
    GetVariantDetailsDTO,
)


class ProductQueryMapper:
    """Создаёт DTO конкретного чтения без I/O и доменных объектов."""

    @staticmethod
    def to_details(row: Mapping[str, Any], locale: str) -> GetProductDetailsDTO:
        """Преобразует карточку с явной locale без fallback."""
        return GetProductDetailsDTO(
            id=row["id"],
            kind=row["kind"],
            product_type_id=row["product_type_id"],
            revision=row["revision"],
            schema_version=row["schema_version"],
            content=row["translations"].get(locale),
            locales=tuple(row["translations"]),
            variant_id=row["variant_id"],
            virtual=row["virtual"],
            downloadable=row["downloadable"],
            variant_content=row["variant_translations"].get(locale),
            variant_locales=tuple(row["variant_translations"]),
        )

    @staticmethod
    def to_list_item(row: Mapping[str, Any], locale: str) -> ProductListItemDTO:
        """Преобразует отдельную строку списка в её собственный контракт."""
        return ProductListItemDTO(
            id=row["id"],
            kind=row["kind"],
            product_type_id=row["product_type_id"],
            revision=row["revision"],
            schema_version=row["schema_version"],
            content=row["translations"].get(locale),
            locales=tuple(row["translations"]),
            variant_id=row["variant_id"],
            virtual=row["virtual"],
            downloadable=row["downloadable"],
            variant_content=row["variant_translations"].get(locale),
            variant_locales=tuple(row["variant_translations"]),
        )

    @staticmethod
    def to_variant(row: Mapping[str, Any], locale: str) -> GetVariantDetailsDTO:
        """Создаёт самостоятельную read-проекцию внутренней позиции."""
        return GetVariantDetailsDTO(
            row["variant_id"],
            row["id"],
            row["revision"],
            row["schema_version"],
            row["variant_translations"].get(locale),
            tuple(row["variant_translations"]),
            row["virtual"],
            row["downloadable"],
        )
