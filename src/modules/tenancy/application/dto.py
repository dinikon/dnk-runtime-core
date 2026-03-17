from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CreateTenantResultDTO:
    tenant_id: UUID
    user_id: UUID
    user_email_id: UUID
    tenant_domain_id: UUID
    tenant_status: str
    user_status: str
    tenant_domain_host: str


@dataclass(frozen=True, slots=True)
class ResolveTenantByHostResultDTO:
    exists: bool
    available: bool
    status: str
    tenant_id: UUID | None
    api_host: str | None


@dataclass(frozen=True, slots=True)
class TenantRequestContextDTO:
    tenant_id: UUID
    tenant_domain_id: UUID
    host: str
    tenant_status: str
    domain_status: str
    api_host: str | None


__all__ = [
    "CreateTenantResultDTO",
    "ResolveTenantByHostResultDTO",
    "TenantRequestContextDTO",
]
