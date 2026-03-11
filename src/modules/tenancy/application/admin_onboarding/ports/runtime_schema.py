from __future__ import annotations

from typing import Protocol
from uuid import UUID


class TenantRuntimeSchemaBootstrapperProtocol(Protocol):
    async def bootstrap_tenant_system_schema(
        self,
        *,
        tenant_id: UUID,
        data_source_id: UUID,
        schema: str,
    ) -> None: ...
