from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ResolveTenantByHostResultDTO:
    """DTO публичного resolve tenant по host для console-клиента."""

    exists: bool
    available: bool
    status: str
    tenant_id: UUID | None
    api_host: str | None


__all__ = ["ResolveTenantByHostResultDTO"]
