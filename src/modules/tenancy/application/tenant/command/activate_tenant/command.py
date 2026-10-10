from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ActivateTenantCommand:
    """Намерение активировать tenant после подготовки обязательных ресурсов."""

    tenant_id: UUID
