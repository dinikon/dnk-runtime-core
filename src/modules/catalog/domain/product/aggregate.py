from dataclasses import dataclass, field
from datetime import datetime
from typing import Self

from src.modules.catalog.domain.product.error import (
    InvalidProductContentError,
    InvalidProductVariantError,
)
from src.modules.catalog.domain.product.value_object.content import ProductContentVO
from src.modules.catalog.domain.product.value_object.identifier import (
    ProductIdVO,
    VariantIdVO,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(eq=False)
class ProductVariant:
    """Единственная продаваемая позиция простого товара."""

    id: VariantIdVO
    sku_id: EntityIdVO


@dataclass(eq=False)
class Product:
    """Простой товар владеет одним Variant и переводами карточки."""

    id: ProductIdVO
    product_type: str
    variants: tuple[ProductVariant, ...]
    created_at: datetime
    updated_at: datetime
    created_by: EntityIdVO
    updated_by: EntityIdVO
    contents: dict[str, ProductContentVO] = field(default_factory=dict)

    @staticmethod
    def _validate_variants(
        product_type: str, variants: tuple[ProductVariant, ...]
    ) -> None:
        if product_type != "SIMPLE" or len(variants) != 1:
            raise InvalidProductVariantError("SIMPLE requires one plain variant.")
        if not isinstance(variants[0], ProductVariant):
            raise InvalidProductVariantError("Product variant is invalid.")

    @property
    def type(self) -> str:
        return self.product_type

    @property
    def variant(self) -> ProductVariant:
        return self.variants[0]

    @classmethod
    def create(
        cls,
        *,
        product_id: ProductIdVO,
        variant_id: VariantIdVO,
        sku_id: EntityIdVO,
        contents: tuple[ProductContentVO, ...],
        actor_id: EntityIdVO,
        now: datetime,
    ) -> Self:
        variants = (ProductVariant(variant_id, sku_id),)
        cls._validate_variants("SIMPLE", variants)
        by_locale: dict[str, ProductContentVO] = {}
        for content in contents:
            if not isinstance(content, ProductContentVO):
                raise InvalidProductContentError("Product content is invalid.")
            code = content.locale.value
            if code in by_locale:
                raise InvalidProductContentError("Duplicate product content locale.")
            by_locale[code] = content
        return cls(
            id=product_id,
            product_type="SIMPLE",
            variants=variants,
            created_at=now,
            updated_at=now,
            created_by=actor_id,
            updated_by=actor_id,
            contents=by_locale,
        )

    @classmethod
    def restore(
        cls,
        *,
        product_id: ProductIdVO,
        product_type: str,
        variants: tuple[ProductVariant, ...],
        created_at: datetime,
        updated_at: datetime,
        created_by: EntityIdVO,
        updated_by: EntityIdVO,
        contents: dict[str, ProductContentVO],
    ) -> Self:
        cls._validate_variants(product_type, variants)
        return cls(
            id=product_id,
            product_type=product_type,
            variants=variants,
            created_at=created_at,
            updated_at=updated_at,
            created_by=created_by,
            updated_by=updated_by,
            contents=dict(contents),
        )

    def replace_content(
        self, content: ProductContentVO, *, actor_id: EntityIdVO, now: datetime
    ) -> None:
        self.contents[content.locale.value] = content
        self.updated_at = now
        self.updated_by = actor_id
