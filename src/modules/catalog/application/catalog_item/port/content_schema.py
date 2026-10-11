from typing import Protocol
from src.modules.catalog.domain.product_type.value_object.schema import (
    ProductTypeSchemaSnapshot,
)


class CatalogItemContentSchemaPort(Protocol):
    """Читает immutable Default schema для проверки записи контента."""

    async def get_default(self, locale: str | None = None) -> ProductTypeSchemaSnapshot:
        """Возвращает единственную системную схему MVP."""
        ...
