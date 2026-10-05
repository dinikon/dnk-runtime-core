from dataclasses import dataclass

from src.modules.catalog.domain.product.error import InvalidProductContentError
from src.modules.catalog.domain.product.value_object.locale import ProductLocaleVO


@dataclass(frozen=True, slots=True)
class ProductContentVO:
    """Текст одной локали; отсутствие перевода не представляется пустым именем."""

    locale: ProductLocaleVO
    name: str
    description: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.locale, ProductLocaleVO):
            raise InvalidProductContentError("Product content locale is invalid.")
        if not isinstance(self.name, str):
            raise InvalidProductContentError("Product name must be a string.")
        name = self.name.strip()
        if not 1 <= len(name) <= 255:
            raise InvalidProductContentError(
                "Product name must contain 1–255 characters."
            )
        object.__setattr__(self, "name", name)
        if self.description is not None and not isinstance(self.description, str):
            raise InvalidProductContentError("Product description must be a string.")
        if self.description is not None:
            object.__setattr__(self, "description", self.description.strip() or None)
