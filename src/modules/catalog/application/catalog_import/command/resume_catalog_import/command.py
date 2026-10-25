from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ResumeCatalogImportCommand:
    """Продолжает остановленный запуск для явно подтверждённого поколения."""

    import_id: UUID
    generation: int
