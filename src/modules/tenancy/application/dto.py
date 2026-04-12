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


@dataclass(frozen=True, slots=True)
class ResolveTenantByHostResultDTO:
    """DTO публичного resolve tenant по host для console-клиента."""

    exists: bool
    available: bool
    status: str
    tenant_id: UUID | None
    api_host: str | None


@dataclass(frozen=True, slots=True)
class TenantRequestContextDTO:
    """DTO request context tenant для внутренних auth-сценариев."""

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
