from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CreateTenantCommandDTO:
    tenant_name: str
    external_id: str
    tenant_domain_host: str
    user_last_name: str
    user_first_name: str
    user_email: str


@dataclass(frozen=True, slots=True)
class CreateTenantResultDTO:
    tenant_id: UUID
    user_id: UUID
    user_email_id: UUID
    tenant_domain_id: UUID
    tenant_status: str
    user_status: str
    tenant_domain_host: str
