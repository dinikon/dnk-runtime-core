from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class GetTenantRequestContextByHostQueryDTO:
    host: str


@dataclass(frozen=True, slots=True)
class TenantRequestContextDTO:
    tenant_id: UUID
    tenant_domain_id: UUID
    host: str
    tenant_status: str
    domain_status: str
    api_host: str | None
