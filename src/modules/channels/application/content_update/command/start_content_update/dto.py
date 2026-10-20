from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class StartContentUpdateResultDTO:
    """Возвращает ID сохранённой подготовки для последующего чтения."""

    run_id: UUID
