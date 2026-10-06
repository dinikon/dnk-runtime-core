from dataclasses import dataclass, field
from datetime import datetime
from types import MappingProxyType
from typing import Mapping, Self

from src.modules.catalog.domain.product.error import (
    InvalidProductCategoriesError,
    InvalidProductContentError,
    InvalidProductVariantError,
    ProductVariantNotFoundError,
)
from src.modules.catalog.domain.product.value_object.content import ProductContentVO
from src.modules.catalog.domain.product.value_object.locale import ProductLocaleVO
from src.modules.catalog.domain.product.value_object.kind import ProductKind
from src.modules.catalog.domain.product.value_object.identifier import (
    ProductIdVO,
    VariantIdVO,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.catalog.domain.category.value_object.identifier import CategoryIdVO


@dataclass(eq=False)
class ProductVariant:
    """Продаваемая позиция внутри Product."""

    id: VariantIdVO
    sku_id: EntityIdVO
    _contents: dict[str, str] = field(default_factory=dict, repr=False)

    @property
    def contents(self) -> Mapping[str, str]:
        return MappingProxyType(self._contents)


@dataclass(eq=False)
class Product:
    """Товар владеет вариантами и переводами карточки."""

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
            or (kind is ProductKind.SIMPLE and len(variants) != 1)
            or (kind is ProductKind.VARIABLE and len(variants) < 2)
        ):
            raise InvalidProductVariantError("Invalid number of product variants.")
        if any(not isinstance(item, ProductVariant) for item in variants):
            raise InvalidProductVariantError("Product variant is invalid.")
        if len({item.id for item in variants}) != len(variants) or len(
            {item.sku_id for item in variants}
        ) != len(variants):
            raise InvalidProductVariantError("Duplicate variant ID or SKU in product.")

    @property
    def variant(self) -> ProductVariant:
        if self.kind is not ProductKind.SIMPLE:
            raise InvalidProductVariantError("VARIABLE has no single variant.")
        return self.variants[0]

    @classmethod
    def create_variable(
        cls,
        *,
        product_id: ProductIdVO,
        variants: tuple[ProductVariant, ...],
        contents: tuple[ProductContentVO, ...],
        actor_id: EntityIdVO,
        now: datetime,
    ) -> Self:
        cls._validate_variants(ProductKind.VARIABLE, variants)
        by_locale: dict[str, ProductContentVO] = {}
        for content in contents:
            if (
                not isinstance(content, ProductContentVO)
                or content.locale.value in by_locale
            ):
                raise InvalidProductContentError(
                    "Duplicate or invalid product content."
                )
            by_locale[content.locale.value] = content
        return cls(
            id=product_id,
            kind=ProductKind.VARIABLE,
            variants=variants,
            created_at=now,
            updated_at=now,
            created_by=actor_id,
            updated_by=actor_id,
            contents=by_locale,
        )

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

    def replace_variant_structure(
        self,
        *,
        kind: ProductKind,
        variants: tuple[ProductVariant, ...],
        actor_id: EntityIdVO,
        now: datetime,
    ) -> None:
        self._validate_variants(kind, variants)
        self.kind = kind
        self.variants = variants
        self.updated_at = now
        self.updated_by = actor_id

    def add_variant(
        self, variant: ProductVariant, *, actor_id: EntityIdVO, now: datetime
    ) -> None:
        if self.kind is not ProductKind.VARIABLE:
            raise InvalidProductVariantError("Use structure change to convert SIMPLE.")
        self.replace_variant_structure(
            kind=self.kind,
            variants=(*self.variants, variant),
            actor_id=actor_id,
            now=now,
        )

    def get_variant(self, variant_id: VariantIdVO) -> ProductVariant:
        for variant in self.variants:
            if variant.id == variant_id:
                return variant
        raise ProductVariantNotFoundError("Variant not found in product.")

    def change_variant_sku(
        self,
        variant_id: VariantIdVO,
        sku_id: EntityIdVO,
        *,
        actor_id: EntityIdVO,
        now: datetime,
    ) -> None:
        variants = tuple(
            (
                ProductVariant(item.id, sku_id, dict(item.contents))
                if item.id == variant_id
                else item
            )
            for item in self.variants
        )
        if not any(item.id == variant_id for item in self.variants):
            raise ProductVariantNotFoundError("Variant not found in product.")
        self.replace_variant_structure(
            kind=self.kind, variants=variants, actor_id=actor_id, now=now
        )

    def remove_variant(
        self, variant_id: VariantIdVO, *, actor_id: EntityIdVO, now: datetime
    ) -> None:
        variants = tuple(item for item in self.variants if item.id != variant_id)
        if len(variants) == len(self.variants):
            raise ProductVariantNotFoundError("Variant not found in product.")
        self.replace_variant_structure(
            kind=self.kind, variants=variants, actor_id=actor_id, now=now
        )

    def replace_variant_content(
        self,
        variant_id: VariantIdVO,
        locale: ProductLocaleVO,
        short_description: str,
        *,
        actor_id: EntityIdVO,
        now: datetime,
    ) -> None:
        if not isinstance(short_description, str) or not short_description.strip():
            raise InvalidProductContentError("Variant short description is required.")
        variant = self.get_variant(variant_id)
        variant._contents[locale.value] = short_description.strip()
        self.updated_at = now
        self.updated_by = actor_id
