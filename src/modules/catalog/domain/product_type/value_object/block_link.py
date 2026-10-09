from dataclasses import dataclass
from enum import StrEnum
from src.modules.catalog.domain.content_block.value_object.identifier import (
    ContentBlockIdVO,
)
from src.modules.catalog.domain.error import InvalidCatalogValueError


class ContentScope(StrEnum):
    """Область контента задаётся связью, а не определением блока."""

    PRODUCT = "PRODUCT"
    VARIANT = "VARIANT"


@dataclass(frozen=True, slots=True)
class ProductTypeContentBlock:
    """Неизменяемая связь блока со scope, обязательностью и порядком."""

    block_id: ContentBlockIdVO
    scope: ContentScope
    required: bool
    position: int

    def __post_init__(self) -> None:
        """Отклоняет недопустимую область и отрицательный порядок."""
        if (
            not isinstance(self.scope, ContentScope)
            or self.position < 0
            or type(self.required) is not bool
        ):
            raise InvalidCatalogValueError("Некорректная связь блока.")
