from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ResolveTenantByHostQueryDTO:
    host: str


@dataclass(frozen=True, slots=True)
class ResolveTenantByHostResultDTO:
    exists: bool
    available: bool
    status: str
    tenant_id: UUID | None
    api_host: str | None
