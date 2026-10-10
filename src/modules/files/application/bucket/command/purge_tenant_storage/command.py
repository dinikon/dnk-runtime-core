from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class PurgeTenantStorageCommand:
    """Вход сценария purge_tenant_storage в доверенном tenant-контексте."""

    tenant_id: UUID
