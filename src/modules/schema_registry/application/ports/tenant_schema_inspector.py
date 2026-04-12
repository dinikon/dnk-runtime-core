from typing import Protocol

from src.modules.schema_registry.application.migration.physical_schema_snapshot import (
    PhysicalSchemaSnapshot,
)


class TenantSchemaInspectorPort(Protocol):
    """Порт чтения фактического состояния физической tenant-схемы."""

    async def schema_exists(self, *, schema_name: str) -> bool:
        """Проверяет наличие физической схемы в backend-хранилище."""
        ...

    async def inspect(self, *, schema_name: str) -> PhysicalSchemaSnapshot:
        """Возвращает канонический snapshot таблиц, колонок, индексов и FK."""
        ...
