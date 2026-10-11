from dataclasses import dataclass
from src.modules.catalog.domain.product_type.value_object.schema import (
    ProductTypeSchemaSnapshot,
)


@dataclass(frozen=True, slots=True)
class GetDefaultProductTypeResultDTO:
    """Системная схема контента без команды редактирования."""

    schema: ProductTypeSchemaSnapshot
    locale: str
