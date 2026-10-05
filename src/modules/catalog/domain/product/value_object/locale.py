import re
from dataclasses import dataclass

from src.modules.catalog.domain.product.error import InvalidProductLocaleError


@dataclass(frozen=True, slots=True)
class ProductLocaleVO:
    """Нормализованный код локали из глобального справочника."""

    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str):
            raise InvalidProductLocaleError("Product locale must be a string.")
        code = self.value.strip()
        if len(code) > 64 or not re.fullmatch(
            r"[a-z]{2,8}(?:-[A-Za-z0-9]{2,8})*", code
        ):
            raise InvalidProductLocaleError("Invalid product locale code.")
        object.__setattr__(self, "value", code)
