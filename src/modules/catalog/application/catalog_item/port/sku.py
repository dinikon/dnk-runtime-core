from typing import Protocol


class CatalogItemSkuPort(Protocol):
    """Проверяет занятость собственного SKU каталога без записи."""

    async def in_use(self, sku: str) -> bool:
        """Возвращает наличие точного нормализованного кода в текущем tenant."""
        ...
