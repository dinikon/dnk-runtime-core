import re
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import Mapping

from src.modules.catalog.domain.product_type.error import (
    InvalidProductTypeError,
    ProductTypeConflictError,
)
from src.modules.catalog.domain.content_block.value_object.content_block import (
    ContentBlockIdVO,
)
from src.modules.catalog.domain.product_type.value_object.product_type_id import (
    ProductTypeIdVO,
)


class ContentScope(StrEnum):
    PRODUCT = "product"
    VARIANT = "variant"


@dataclass(frozen=True, slots=True)
class ProductTypeContentBlock:
    block_id: ContentBlockIdVO
    scope: ContentScope
    required: bool
    position: int

    def __post_init__(self) -> None:
        if not isinstance(self.block_id, ContentBlockIdVO) or not isinstance(
            self.scope, ContentScope
        ):
            raise InvalidProductTypeError("Invalid content block assignment.")
        if (
            type(self.required) is not bool
            or type(self.position) is not int
            or self.position < 0
        ):
            raise InvalidProductTypeError("Invalid content block settings.")


@dataclass(eq=False)
class ProductType:
    id: ProductTypeIdVO
    code: str
    is_system: bool
    schema_version: int
    blocks: tuple[ProductTypeContentBlock, ...]
    _translations: dict[str, str] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        *,
        id: ProductTypeIdVO,
        code: str,
        translations: Mapping[str, str],
        blocks: tuple[ProductTypeContentBlock, ...] = (),
        is_system: bool = False,
    ) -> "ProductType":
        if not isinstance(code, str) or not re.fullmatch(
            r"[a-z][a-z0-9_]{0,127}", code.strip().lower()
        ):
            raise InvalidProductTypeError("Invalid product type code.")
        if not translations or any(
            not isinstance(name, str) or not 1 <= len(name.strip()) <= 255
            for name in translations.values()
        ):
            raise InvalidProductTypeError("Product type needs valid translations.")
        cls.validate_blocks(blocks)
        return cls(
            id,
            code.strip().lower(),
            is_system,
            1,
            tuple(sorted(blocks, key=lambda item: (item.scope.value, item.position))),
            {k: v.strip() for k, v in translations.items()},
        )

    @classmethod
    def restore(
        cls,
        *,
        id: ProductTypeIdVO,
        code: str,
        is_system: bool,
        schema_version: int,
        translations: Mapping[str, str],
        blocks: tuple[ProductTypeContentBlock, ...],
    ) -> "ProductType":
        if schema_version < 1:
            raise InvalidProductTypeError("Invalid product type schema version.")
        product_type = cls.create(
            id=id,
            code=code,
            is_system=is_system,
            translations=translations,
            blocks=blocks,
        )
        product_type.schema_version = schema_version
        return product_type

    @staticmethod
    def validate_blocks(blocks: tuple[ProductTypeContentBlock, ...]) -> None:
        keys = [(item.scope, item.block_id) for item in blocks]
        positions = [(item.scope, item.position) for item in blocks]
        if len(set(keys)) != len(keys) or len(set(positions)) != len(positions):
            raise InvalidProductTypeError("Duplicate block or position within scope.")

    @property
    def translations(self) -> Mapping[str, str]:
        return MappingProxyType(self._translations)

    def set_translation(self, locale: str, name: str) -> None:
        if not isinstance(name, str) or not 1 <= len(name.strip()) <= 255:
            raise InvalidProductTypeError(
                "Product type name must contain 1–255 characters."
            )
        self._translations[locale] = name.strip()

    def replace_translations(self, translations: Mapping[str, str]) -> None:
        if not translations or any(
            not isinstance(name, str) or not 1 <= len(name.strip()) <= 255
            for name in translations.values()
        ):
            raise InvalidProductTypeError("Product type needs valid translations.")
        self._translations = {
            locale: name.strip() for locale, name in translations.items()
        }

    def replace_blocks(self, blocks: tuple[ProductTypeContentBlock, ...]) -> None:
        self.validate_blocks(blocks)
        blocks = tuple(
            sorted(blocks, key=lambda item: (item.scope.value, item.position))
        )
        if self.blocks == blocks:
            return
        if self.is_system:
            raise ProductTypeConflictError("System product type cannot be changed.")
        self.blocks = blocks
        self.schema_version += 1
