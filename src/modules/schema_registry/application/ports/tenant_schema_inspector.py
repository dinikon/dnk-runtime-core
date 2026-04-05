from typing import Protocol


class TenantSchemaSnapshotDTO(Protocol):
    schema_name: str


class TenantSchemaInspectorPort(Protocol):
    async def schema_exists(self, *, schema_name: str) -> bool: ...
    async def inspect(self, *, schema_name: str): ...
