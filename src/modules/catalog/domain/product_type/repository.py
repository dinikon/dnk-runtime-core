from typing import Protocol
from src.modules.catalog.domain.product_type.aggregate import ProductType


class ProductTypeRepositoryProtocol(Protocol):
    """Хранит полный агрегат схемы в tenant-сессии внешнего UoW."""

    async def get_by_code(self, code: str) -> ProductType | None:
        """Восстанавливает схему или возвращает отсутствие без создания данных."""
        ...

    async def add(self, product_type: ProductType) -> None:
        """Добавляет схему, определения блоков и переводы без commit."""
        ...
