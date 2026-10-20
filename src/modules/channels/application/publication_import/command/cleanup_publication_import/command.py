from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CleanupPublicationImportCommand:
    """Освобождает только временные файлы одной закрытой подготовки."""

    tenant_id: UUID
    preparation_id: UUID
