from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class PrepareExportArtifactPageCommand:
    """Передаёт курсор ограниченной части неизменяемого файла текущего шага."""

    run_id: UUID
    sequence: int
    after: UUID | None = None
