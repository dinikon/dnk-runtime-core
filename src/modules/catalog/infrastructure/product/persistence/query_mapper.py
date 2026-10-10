from src.modules.catalog.application.product.query.get_product.dto import (
    ProductAttributeValueDetailsDTO,
)
from collections.abc import Mapping
from typing import Any
from src.modules.catalog.domain.product.policy.title import VariantTitlePolicy
from src.modules.catalog.application.product.query.get_product.dto import (
    GetProductDetailsDTO,
    ProductAxisDetailsDTO,
    ProductVariantDetailsDTO,
)
from src.modules.catalog.application.product.query.get_variant.dto import (
    GetVariantDetailsDTO,
)
from src.modules.catalog.application.product.query.list_products.dto import (
    ProductListItemDTO,
)


class ProductQueryMapper:
    """Создаёт собственные read DTO из SQL-проекций без восстановления Product."""

    @staticmethod
    def _title(
        row: Mapping[str, Any], variant: Mapping[str, Any], locale: str
    ) -> tuple[str | None, str | None]:
        """Применяет чистую доменную политику Title для VARIABLE той же locale."""
        if row["kind"] != "variable" or row["variant_title_id"] is None:
            return None, None
        value, source = VariantTitlePolicy.resolve(
            str(row["variant_title_id"]),
            (
                row["translations"].get(locale)
                if row["title_id"] == row["variant_title_id"]
                else None
            ),
            variant["translations"].get(locale),
        )
        return value, None if source is None else source.value

    @staticmethod
    def _product_title(row: Mapping[str, Any], locale: str) -> str | None:
        """Читает собственный системный Title без fallback и выдуманного названия."""
        content = row["translations"].get(locale)
        return (
            None
            if content is None or row["title_id"] is None
            else content.get(str(row["title_id"]))
        )

    @staticmethod
    def to_details(row: Mapping[str, Any], locale: str) -> GetProductDetailsDTO:
        """Преобразует полную карточку и все позиции выбранной locale."""
        variants = []
        for variant in row["variants"]:
            title, source = ProductQueryMapper._title(row, variant, locale)
            variants.append(
                ProductVariantDetailsDTO(
                    variant["id"],
                    variant["selection"],
                    variant["virtual"],
                    variant["downloadable"],
                    variant["translations"].get(locale),
                    tuple(variant["translations"]),
                    title,
                    source,
                )
            )
        return GetProductDetailsDTO(
            row["id"],
            row["kind"],
            row["product_type_id"],
            row["revision"],
            row["schema_version"],
            row["translations"].get(locale),
            tuple(row["translations"]),
            ProductQueryMapper._product_title(row, locale),
            tuple(
                ProductAxisDetailsDTO(a["attribute_id"], a["option_ids"], a["position"])
                for a in row["axes"]
            ),
            row["default_selection"],
            tuple(variants),
            tuple(
                ProductAttributeValueDetailsDTO(
                    v["attribute_id"], v["option_id"], v["visible"], v["position"]
                )
                for v in row["attribute_values"]
            ),
            tuple(c["category_id"] for c in row["categories"]),
            next(
                (c["category_id"] for c in row["categories"] if c["is_primary"]), None
            ),
            row["tag_ids"],
        )

    @staticmethod
    def to_list_item(row: Mapping[str, Any], locale: str) -> ProductListItemDTO:
        """Преобразует строку списка в его собственный контракт."""
        return ProductListItemDTO(
            row["id"],
            row["kind"],
            row["product_type_id"],
            row["revision"],
            row["schema_version"],
            row["translations"].get(locale),
            tuple(row["translations"]),
            ProductQueryMapper._product_title(row, locale),
            row["variant_count"],
        )

    @staticmethod
    def to_variant(
        row: Mapping[str, Any], variant: Mapping[str, Any], locale: str
    ) -> GetVariantDetailsDTO:
        """Преобразует отдельную позицию в самостоятельный результат get_variant."""
        title, source = ProductQueryMapper._title(row, variant, locale)
        return GetVariantDetailsDTO(
            variant["id"],
            row["id"],
            row["kind"],
            row["revision"],
            row["schema_version"],
            variant["selection"],
            variant["translations"].get(locale),
            tuple(variant["translations"]),
            variant["virtual"],
            variant["downloadable"],
            title,
            source,
        )
