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
    def __init__(
        self,
        inspector: TenantSchemaInspectorPort,
        executor: TenantSchemaExecutorPort,
    ) -> None:
        self._inspector = inspector
        self._executor = executor

    async def ensure_schema_absent(self, *, schema_name: str) -> None:
        exists = await self._inspector.schema_exists(schema_name=schema_name)
        if exists:
            raise PhysicalSchemaAlreadyExistsError(schema_name)

    async def inspect_required_schema(
        self,
        *,
        schema_name: str,
    ) -> PhysicalSchemaSnapshot:
        exists = await self._inspector.schema_exists(schema_name=schema_name)
        if not exists:
            raise PhysicalSchemaNotFoundError(schema_name)
        return await self._inspector.inspect(schema_name=schema_name)

    async def apply_plan(self, *, plan: MigrationPlan) -> None:
        if plan.is_empty:
            return
        await self._executor.execute(plan=plan)
