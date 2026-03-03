from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True, slots=True)
class TenantRequestContext:
    tenant_id: UUID
    tenant_domain_id: UUID
    host: str
    tenant_status: str
    domain_status: str
    api_host: str | None


class TenantContextReaderPort(Protocol):
    async def get_by_host(self, host: str) -> TenantRequestContext: ...
