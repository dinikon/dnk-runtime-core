from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class PreparePublicationImportStepCommand:
    """Адресует один шаг durable очереди."""

    tenant_id: UUID
    preparation_id: UUID
    sequence: int
