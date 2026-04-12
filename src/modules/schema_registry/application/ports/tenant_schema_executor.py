from typing import Protocol

from src.modules.schema_registry.application.migration.plan import MigrationPlan


class TenantSchemaExecutorPort(Protocol):
    """Порт применения migration plan к физической tenant-схеме."""

    async def execute(self, *, plan: MigrationPlan) -> None:
        """Выполняет операции плана в порядке, заданном application-слоем."""
        ...
