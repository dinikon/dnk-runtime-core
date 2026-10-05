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


@dataclass(frozen=True, slots=True)
class VariantSelection:
    attribute_id: EntityIdVO
    option_id: EntityIdVO


@dataclass(frozen=True, slots=True)
class ProductVariant:
    """Продаваемая позиция и её выбор значений атрибутов."""

    id: VariantIdVO
    sku_id: EntityIdVO
    selections: tuple[VariantSelection, ...] = ()

    def __post_init__(self) -> None:
        if len(self.selections) > 16:
            raise InvalidProductVariantError(
                "A variant supports at most 16 attributes."
            )
        identifiers = [item.attribute_id.uuid for item in self.selections]
        if len(identifiers) != len(set(identifiers)):
            raise InvalidProductVariantError("Duplicate variant attribute.")

    @property
    def combination_key(self) -> str:
        if not self.selections:
            return "SIMPLE"
        return ";".join(
            f"{item.attribute_id.uuid}={item.option_id.uuid}"
            for item in sorted(
                self.selections, key=lambda value: value.attribute_id.uuid
            )
        )


@dataclass(slots=True)
class Product:
    """Товар владеет вариантами и локализованным контентом."""

    id: ProductIdVO
    product_type: str
    variants: tuple[ProductVariant, ...]
    created_at: datetime
    updated_at: datetime
    created_by: EntityIdVO
    updated_by: EntityIdVO
    contents: dict[str, ProductContentVO] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.product_type not in {"SIMPLE", "VARIABLE"}:
            raise InvalidProductVariantError("Product type is invalid.")
        if self.product_type == "SIMPLE":
            if len(self.variants) != 1 or self.variants[0].selections:
                raise InvalidProductVariantError("SIMPLE requires one plain variant.")
        else:
            if len(self.variants) < 2:
                raise InvalidProductVariantError(
                    "VARIABLE requires at least two variants."
                )
            dimensions = {
                item.attribute_id.uuid for item in self.variants[0].selections
            }
            if not dimensions or any(
                {item.attribute_id.uuid for item in variant.selections} != dimensions
                for variant in self.variants
            ):
                raise InvalidProductVariantError(
                    "VARIABLE variants must use the same attributes."
                )
            keys = [variant.combination_key for variant in self.variants]
            if len(keys) != len(set(keys)):
                raise InvalidProductVariantError("Duplicate variant combination.")
        ids = [variant.id.uuid for variant in self.variants]
        if len(ids) != len(set(ids)):
            raise InvalidProductVariantError("Duplicate variant identifier.")

    @property
    def type(self) -> str:
        return self.product_type

    @property
    def variant(self) -> ProductVariant:
        """Контракт единственной позиции SIMPLE."""
        if self.type != "SIMPLE":
            raise InvalidProductVariantError("VARIABLE has no single variant.")
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
        return cls.create_simple(
            product_id=product_id,
            variant_id=variant_id,
            sku_id=sku_id,
            contents=contents,
            actor_id=actor_id,
            now=now,
        )

    @classmethod
    def create_simple(
        cls,
        *,
        product_id: ProductIdVO,
        variant_id: VariantIdVO,
        sku_id: EntityIdVO,
        contents: tuple[ProductContentVO, ...],
        actor_id: EntityIdVO,
        now: datetime,
    ) -> Self:
        return cls._create(
            product_id=product_id,
            product_type="SIMPLE",
            variants=(ProductVariant(variant_id, sku_id),),
            contents=contents,
            actor_id=actor_id,
            now=now,
        )

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
        return cls._create(
            product_id=product_id,
            product_type="VARIABLE",
            variants=variants,
            contents=contents,
            actor_id=actor_id,
            now=now,
        )

    @classmethod
    def _create(
        cls,
        *,
        product_id: ProductIdVO,
        product_type: str,
        variants: tuple[ProductVariant, ...],
        contents: tuple[ProductContentVO, ...],
        actor_id: EntityIdVO,
        now: datetime,
    ) -> Self:
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
            product_type=product_type,
            variants=variants,
            created_at=now,
            updated_at=now,
            created_by=actor_id,
            updated_by=actor_id,
            contents=by_locale,
        )

    def replace_content(
        self, content: ProductContentVO, *, actor_id: EntityIdVO, now: datetime
    ) -> None:
        self.contents[content.locale.value] = content
        self.updated_at = now
        self.updated_by = actor_id
