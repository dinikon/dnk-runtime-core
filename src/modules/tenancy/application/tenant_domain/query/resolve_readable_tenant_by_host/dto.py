from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ResolveReadableTenantByHostResultDTO:
    """Идентифицирует tenant, чьи данные доступны для чтения по хосту."""

    tenant_id: UUID
