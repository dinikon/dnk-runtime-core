from typing import Protocol
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.catalog.domain.catalog_import.aggregate import CatalogImport


class CatalogImportRepository(Protocol):
    """Хранение агрегата на общей tenant-транзакции."""

    async def get(self, identifier: EntityIdVO, *, lock: bool = False) -> CatalogImport:
        """Загружает агрегат, при необходимости блокируя его."""
        ...

    async def by_key(self, key: str) -> CatalogImport | None:
        """Находит исходный запуск повторённого запроса."""
        ...

    async def save(self, entity: CatalogImport) -> None:
        """Сохраняет состояние без собственного commit."""
        ...

    async def lock_lane(self) -> None:
        """Сериализует запуск импорта внутри tenant."""
        ...

    async def executing(self, exclude: EntityIdVO) -> bool:
        """Проверяет наличие другого запущенного импорта."""
        ...
