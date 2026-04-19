from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CreateTenantResultDTO:
    """DTO результата создания tenant и администратора."""

    tenant_id: UUID
    user_id: UUID
    user_email_id: UUID
    tenant_domain_id: UUID
    tenant_status: str
    user_status: str
    tenant_domain_host: str


__all__ = ["CreateTenantResultDTO"]
