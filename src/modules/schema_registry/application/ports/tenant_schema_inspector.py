from typing import Protocol

from src.modules.schema_registry.domain.migration.snapshot import (
    PhysicalSchemaSnapshot,
)


class TenantSchemaInspectorPort(Protocol):
    async def schema_exists(self, *, schema_name: str) -> bool: ...
    async def inspect(self, *, schema_name: str) -> PhysicalSchemaSnapshot: ...
