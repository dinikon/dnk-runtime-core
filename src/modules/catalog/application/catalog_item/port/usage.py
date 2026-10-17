from typing import Protocol
from src.modules.catalog.domain.catalog_item.value_object.identifier import (
    CatalogItemIdVO,
)


class CatalogItemUsagePort(Protocol):
    """Публичная проверка внешних зависимостей перед удалением товара."""

    async def used_ids(
        self, identifiers: tuple[CatalogItemIdVO, ...]
    ) -> frozenset[CatalogItemIdVO]:
        """Возвращает только идентичности с активными внешними ссылками."""
        ...
