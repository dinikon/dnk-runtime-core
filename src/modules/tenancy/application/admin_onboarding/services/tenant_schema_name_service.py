from __future__ import annotations

from typing import Protocol
from uuid import UUID


class TenantSchemaNameServiceProtocol(Protocol):
    def build(self, tenant_id: UUID) -> str: ...


class TenantSchemaNameService:
    def build(self, tenant_id: UUID) -> str:
        return f"dnk_schema_{tenant_id}"
