from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class LockReadyFileCommand:
    """Фиксирует доступность файла до завершения транзакции потребителя."""

    tenant_id: UUID
    file_id: UUID
