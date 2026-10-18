from typing import Protocol
from src.modules.catalog.domain.product_type.value_object.schema import (
    ProductTypeSchemaSnapshot,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class CatalogItemContentSchemaPort(Protocol):
    """Читает существующие схемы для выбора типа и проверки контента."""

    async def get_by_code(
        self, code: str = "default", locale: str | None = None
    ) -> ProductTypeSchemaSnapshot:
        """Возвращает схему текущего tenant по коду без инициализации."""
        ...

    async def get_by_id(
        self, identifier: EntityIdVO, locale: str | None = None
    ) -> ProductTypeSchemaSnapshot:
        """Возвращает схему сохранённого товара по его реальному UUID."""
        ...
