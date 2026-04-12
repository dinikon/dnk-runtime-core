from __future__ import annotations

from src.modules.schema_registry.application.ports.tenant_schema_executor import (
    TenantSchemaExecutorPort,
)
from src.modules.schema_registry.application.ports.tenant_schema_inspector import (
    TenantSchemaInspectorPort,
)
from src.modules.schema_registry.domain.error import (
    PhysicalSchemaAlreadyExistsError,
    PhysicalSchemaNotFoundError,
)
from src.modules.schema_registry.application.migration.plan import MigrationPlan
from src.modules.schema_registry.application.migration.physical_schema_snapshot import (
    PhysicalSchemaSnapshot,
)


class PostgresSchemaService:
    """Координирует инспекцию и применение планов для tenant PostgreSQL-схем."""

    def __init__(
        self,
        inspector: TenantSchemaInspectorPort,
        executor: TenantSchemaExecutorPort,
    ) -> None:
        """Инициализирует сервис портами инспектора и исполнителя миграций."""
        self._inspector = inspector
        self._executor = executor

    async def ensure_schema_absent(self, *, schema_name: str) -> None:
        """Проверяет, что физической схемы еще нет, иначе поднимает доменную ошибку."""
        exists = await self._inspector.schema_exists(schema_name=schema_name)
        if exists:
            raise PhysicalSchemaAlreadyExistsError(schema_name)

    async def inspect_required_schema(
        self,
        *,
        schema_name: str,
    ) -> PhysicalSchemaSnapshot:
        """Возвращает snapshot существующей физической схемы tenant."""
        exists = await self._inspector.schema_exists(schema_name=schema_name)
        if not exists:
            raise PhysicalSchemaNotFoundError(schema_name)
        return await self._inspector.inspect(schema_name=schema_name)

    async def apply_plan(self, *, plan: MigrationPlan) -> None:
        """Применяет migration plan, пропуская пустые планы без обращения к БД."""
        if plan.is_empty:
            return
        await self._executor.execute(plan=plan)
