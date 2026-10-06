from dataclasses import dataclass, field
from datetime import datetime
from types import MappingProxyType
from typing import Mapping, Self
from uuid import UUID

from src.modules.catalog.domain.product.error import (
    InvalidProductCategoriesError,
    InvalidProductContentError,
    ProductContentSchemaConflictError,
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
from src.modules.catalog.domain.product_type.value_object.product_type_id import (
    ProductTypeIdVO,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.catalog.domain.category.value_object.identifier import CategoryIdVO


@dataclass(eq=False)
class ProductVariant:
    """Продаваемая позиция внутри Product."""

    id: VariantIdVO
    sku_id: EntityIdVO
    _contents: dict[str, ProductContentVO] = field(default_factory=dict, repr=False)

    @property
    def contents(self) -> Mapping[str, ProductContentVO]:
        return MappingProxyType(self._contents)


@dataclass(eq=False)
class Product:
    """Товар владеет вариантами и переводами карточки."""

    id: ProductIdVO
    kind: ProductKind
    product_type_id: ProductTypeIdVO
    _variants: tuple[ProductVariant, ...]
    created_at: datetime
    updated_at: datetime
    created_by: EntityIdVO
    updated_by: EntityIdVO
    _contents: dict[str, ProductContentVO] = field(default_factory=dict)
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

    @property
    def variants(self) -> tuple[ProductVariant, ...]:
        return tuple(
            ProductVariant(item.id, item.sku_id, dict(item.contents))
            for item in self._variants
        )

    @property
    def contents(self) -> Mapping[str, ProductContentVO]:
        return MappingProxyType(self._contents)

    @classmethod
    def create_variable(
        cls,
        *,
        product_id: ProductIdVO,
        product_type_id: ProductTypeIdVO,
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
            product_type_id=product_type_id,
            _variants=tuple(
                ProductVariant(item.id, item.sku_id, dict(item.contents))
                for item in variants
            ),
            created_at=now,
            updated_at=now,
            created_by=actor_id,
            updated_by=actor_id,
            _contents=by_locale,
        )

    @classmethod
    def create(
        cls,
        *,
        product_id: ProductIdVO,
        product_type_id: ProductTypeIdVO,
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
            product_type_id=product_type_id,
            _variants=tuple(
                ProductVariant(item.id, item.sku_id, dict(item.contents))
                for item in variants
            ),
            created_at=now,
            updated_at=now,
            created_by=actor_id,
            updated_by=actor_id,
            _contents=by_locale,
        )

    @classmethod
    def restore(
        cls,
        *,
        product_id: ProductIdVO,
        product_type_id: ProductTypeIdVO,
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
        if any(
            not isinstance(content, ProductContentVO) or locale != content.locale.value
            for locale, content in contents.items()
        ):
            raise InvalidProductContentError("Product content is invalid.")
        cls._validate_categories(category_ids, primary_category_id)
        return cls(
            id=product_id,
            kind=kind,
            product_type_id=product_type_id,
            _variants=tuple(
                ProductVariant(item.id, item.sku_id, dict(item.contents))
                for item in variants
            ),
            created_at=created_at,
            updated_at=updated_at,
            created_by=created_by,
            updated_by=updated_by,
            _contents=dict(contents),
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
        self._validate_categories(category_ids, primary_category_id)
        self.category_ids = category_ids
        self.primary_category_id = primary_category_id
        self.updated_at = now
        self.updated_by = actor_id

    @staticmethod
    def _validate_categories(
        category_ids: tuple[CategoryIdVO, ...],
        primary_category_id: CategoryIdVO | None,
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

    def replace_content(
        self, content: ProductContentVO, *, actor_id: EntityIdVO, now: datetime
    ) -> None:
        self._contents[content.locale.value] = content
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
        self._variants = tuple(
            ProductVariant(item.id, item.sku_id, dict(item.contents))
            for item in variants
        )
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
        variant = self._find_variant(variant_id)
        return ProductVariant(variant.id, variant.sku_id, dict(variant.contents))

    def _find_variant(self, variant_id: VariantIdVO) -> ProductVariant:
        for variant in self._variants:
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
        content: ProductContentVO,
        *,
        actor_id: EntityIdVO,
        now: datetime,
    ) -> None:
        variant = self._find_variant(variant_id)
        variant._contents[content.locale.value] = content
        self.updated_at = now
        self.updated_by = actor_id

    def remove_content(
        self, locale: ProductLocaleVO, *, actor_id: EntityIdVO, now: datetime
    ) -> None:
        self._contents.pop(locale.value, None)
        self.updated_at = now
        self.updated_by = actor_id

    def remove_variant_content(
        self,
        variant_id: VariantIdVO,
        locale: ProductLocaleVO,
        *,
        actor_id: EntityIdVO,
        now: datetime,
    ) -> None:
        self._find_variant(variant_id)._contents.pop(locale.value, None)
        self.updated_at = now
        self.updated_by = actor_id

    def change_product_type(
        self, type_id: ProductTypeIdVO, *, actor_id: EntityIdVO, now: datetime
    ) -> None:
        self.product_type_id = type_id
        self.updated_at = now
        self.updated_by = actor_id

    def ensure_content_compatible(
        self,
        *,
        product_allowed: frozenset[UUID],
        product_required: frozenset[UUID],
        variant_allowed: frozenset[UUID],
        variant_required: frozenset[UUID],
    ) -> None:
        """Проверяет все сохранённые переводы перед сменой ProductType."""
        for contents, allowed, required in (
            (self.contents, product_allowed, product_required),
            *(
                (item.contents, variant_allowed, variant_required)
                for item in self.variants
            ),
        ):
            for content in contents.values():
                saved = set(content.values)
                if not saved <= allowed or not required <= saved:
                    raise ProductContentSchemaConflictError(
                        "Saved content is incompatible with product type."
                    )
