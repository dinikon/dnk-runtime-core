from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ResumeBatchExportResultDTO:
    """Возвращает принятую операцию восстановления или продолжающийся шаг."""

    run_id: UUID
