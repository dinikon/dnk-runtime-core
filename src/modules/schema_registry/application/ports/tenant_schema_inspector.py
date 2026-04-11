from typing import Protocol

from src.modules.schema_registry.application.migration.physical_schema_snapshot import (
    PhysicalSchemaSnapshot,
)


class TenantSchemaInspectorPort(Protocol):
    async def schema_exists(self, *, schema_name: str) -> bool: ...
    async def inspect(self, *, schema_name: str) -> PhysicalSchemaSnapshot: ...
