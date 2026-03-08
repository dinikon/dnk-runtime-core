from __future__ import annotations

from typing import Protocol


class TenantSchemaProvisionerProtocol(Protocol):
    async def create_schema(self, schema: str) -> None: ...
