from dataclasses import dataclass, field
from datetime import datetime
from typing import Self

from src.modules.catalog.domain.product.error import (
    InvalidProductCategoriesError,
    InvalidProductContentError,
    InvalidProductVariantError,
)
from src.modules.catalog.domain.product.value_object.content import ProductContentVO
from src.modules.catalog.domain.product.value_object.kind import ProductKind
from src.modules.catalog.domain.product.value_object.identifier import (
    ProductIdVO,
    VariantIdVO,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.catalog.domain.category.value_object.identifier import CategoryIdVO


@dataclass(eq=False)
class ProductVariant:
    """Единственная продаваемая позиция простого товара."""

    id: VariantIdVO
    sku_id: EntityIdVO


@dataclass(eq=False)
class Product:
    """Простой товар владеет одним Variant и переводами карточки."""

    id: ProductIdVO
    kind: ProductKind
    variants: tuple[ProductVariant, ...]
    created_at: datetime
    updated_at: datetime
    created_by: EntityIdVO
    updated_by: EntityIdVO
    contents: dict[str, ProductContentVO] = field(default_factory=dict)
    category_ids: tuple[CategoryIdVO, ...] = ()
    primary_category_id: CategoryIdVO | None = None

    @staticmethod
    def _validate_variants(
        kind: ProductKind, variants: tuple[ProductVariant, ...]
    ) -> None:
        if (
            not isinstance(kind, ProductKind)
            or kind is not ProductKind.SIMPLE
            or len(variants) != 1
        ):
            raise InvalidProductVariantError("SIMPLE requires one plain variant.")
        if not isinstance(variants[0], ProductVariant):
            raise InvalidProductVariantError("Product variant is invalid.")

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
        cls._validate_variants(ProductKind.SIMPLE, variants)
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
            kind=ProductKind.SIMPLE,
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
        kind: ProductKind,
        variants: tuple[ProductVariant, ...],
        created_at: datetime,
        updated_at: datetime,
        created_by: EntityIdVO,
        updated_by: EntityIdVO,
        contents: dict[str, ProductContentVO],
        category_ids: tuple[CategoryIdVO, ...] = (),
        primary_category_id: CategoryIdVO | None = None,
    ) -> Self:
        cls._validate_variants(kind, variants)
        return cls(
            id=product_id,
            kind=kind,
            variants=variants,
            created_at=created_at,
            updated_at=updated_at,
            created_by=created_by,
            updated_by=updated_by,
            contents=dict(contents),
            category_ids=category_ids,
            primary_category_id=primary_category_id,
        )

    def replace_categories(
        self,
        *,
        category_ids: tuple[CategoryIdVO, ...],
        primary_category_id: CategoryIdVO | None,
        actor_id: EntityIdVO,
        now: datetime,
    ) -> None:
        if any(not isinstance(item, CategoryIdVO) for item in category_ids):
            raise InvalidProductCategoriesError("Invalid category identifier.")
        if len(set(category_ids)) != len(category_ids):
            raise InvalidProductCategoriesError("Duplicate category identifier.")
        if (not category_ids and primary_category_id is not None) or (
            category_ids and primary_category_id not in category_ids
        ):
            raise InvalidProductCategoriesError(
                "Primary category must belong to the product."
            )
        self.category_ids = category_ids
        self.primary_category_id = primary_category_id
        self.updated_at = now
        self.updated_by = actor_id

    def replace_content(
        self, content: ProductContentVO, *, actor_id: EntityIdVO, now: datetime
    ) -> None:
        self.contents[content.locale.value] = content
        self.updated_at = now
        self.updated_by = actor_id
