from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class RegisterSystemStorageCommand:
    """Вход сценария register_system_storage в доверенном tenant-контексте."""

    tenant_id: UUID
