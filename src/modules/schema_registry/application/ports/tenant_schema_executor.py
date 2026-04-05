from typing import Protocol

from src.modules.schema_registry.domain.migration.plan import MigrationPlan


class TenantSchemaExecutorPort(Protocol):
    async def execute(self, *, plan: MigrationPlan) -> None: ...
