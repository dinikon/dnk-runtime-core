from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ListProvidersQuery:
    """Вход сценария list_providers в доверенном tenant-контексте."""

    tenant_id: UUID
