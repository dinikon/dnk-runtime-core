from typing import Protocol

from src.modules.schema_registry.domain.datasource.entity import DataSourceEntity
from src.modules.shared import EntityIdVO


class DataSourceRepositoryProtocol(Protocol):
    """Порт хранения datasource metadata schema_registry."""

    async def get_by_tenant_id(
        self, *, tenant_id: EntityIdVO
    ) -> DataSourceEntity | None:
        """Возвращает datasource tenant или None."""
        ...

    async def add(self, datasource: DataSourceEntity) -> None:
        """Добавляет новый datasource в хранилище."""
        ...

    async def update(self, datasource: DataSourceEntity) -> None:
        """Сохраняет изменения существующего datasource."""
        ...
