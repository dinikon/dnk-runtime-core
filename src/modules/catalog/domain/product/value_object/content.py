from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping
from uuid import UUID

from src.modules.catalog.domain.product.error import InvalidProductContentError
from src.modules.catalog.domain.product.value_object.locale import ProductLocaleVO


@dataclass(frozen=True, slots=True)
class ProductContentVO:
    """Локализованные значения блоков одного владельца."""

    locale: ProductLocaleVO
    values: Mapping[UUID, str]

    def __post_init__(self) -> None:
        if not isinstance(self.locale, ProductLocaleVO) or not isinstance(
            self.values, Mapping
        ):
            raise InvalidProductContentError("Invalid product content.")
        if any(
            not isinstance(key, UUID) or not isinstance(value, str) or not value.strip()
            for key, value in self.values.items()
        ):
            raise InvalidProductContentError(
                "Content values must be non-empty strings."
            )
        object.__setattr__(self, "values", MappingProxyType(dict(self.values)))
