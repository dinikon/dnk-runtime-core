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

    async def table_has_rows(self, *, schema_name: str, table_name: str) -> bool:
        """Проверяет, есть ли данные в физической таблице."""
        ...

    async def column_has_non_null_values(
        self,
        *,
        schema_name: str,
        table_name: str,
        column_name: str,
    ) -> bool:
        """Проверяет, есть ли non-null значения в колонке таблицы."""
        ...
