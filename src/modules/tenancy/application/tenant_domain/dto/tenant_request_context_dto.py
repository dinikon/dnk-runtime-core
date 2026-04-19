from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class TenantRequestContextDTO:
    """DTO request context tenant для внутренних auth-сценариев."""

    tenant_id: UUID
    tenant_domain_id: UUID
    host: str
    tenant_status: str
    domain_status: str
    api_host: str | None


__all__ = ["TenantRequestContextDTO"]
