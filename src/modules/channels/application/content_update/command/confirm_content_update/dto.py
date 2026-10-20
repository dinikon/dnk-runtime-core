from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ConfirmContentUpdateResultDTO:
    """Возвращает ID принятой операции без ложного результата внешней записи."""

    run_id: UUID
