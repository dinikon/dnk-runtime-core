from typing import Protocol

from src.modules.schema_registry.application.migration.plan import MigrationPlan


class TenantSchemaExecutorPort(Protocol):
    async def execute(self, *, plan: MigrationPlan) -> None: ...
