from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class PurgeFileCommand:
    """Передаёт доверенные идентификаторы текущего удаления файла."""

    tenant_id: UUID
    file_id: UUID
    job_id: UUID
