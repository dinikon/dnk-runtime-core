from __future__ import annotations

from typing import Protocol
from uuid import UUID


class TenantSchemaNameServiceProtocol(Protocol):
    def build_schema_name(self, tenant_id: UUID) -> str: ...


class TenantSchemaNameService:
    def build_schema_name(self, tenant_id: UUID) -> str:
        return f"dnk-{tenant_id}"
