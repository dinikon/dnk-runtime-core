from __future__ import annotations

from typing import Protocol
from uuid import UUID


class RuntimeSchemaBootstrapperProtocol(Protocol):
    async def bootstrap_tenant(self, tenant_id: UUID) -> None: ...


__all__ = ["RuntimeSchemaBootstrapperProtocol"]
