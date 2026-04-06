from __future__ import annotations

from src.modules.schema_registry.application.ports.tenant_schema_executor import (
    TenantSchemaExecutorPort,
)
from src.modules.schema_registry.application.ports.tenant_schema_inspector import (
    TenantSchemaInspectorPort,
)
from src.modules.schema_registry.domain.error import PhysicalSchemaAlreadyExistsError
from src.modules.schema_registry.domain.migration.plan import MigrationPlan


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

    async def inspect_schema(self, *, schema_name: str):
        return await self._inspector.inspect(schema_name=schema_name)

    async def apply_plan(self, *, plan: MigrationPlan) -> None:
        if plan.is_empty:
            return
        await self._executor.execute(plan=plan)
