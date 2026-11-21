from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class PrepareInternalMoveQuery:
    """Передаёт документ для подготовки фактического состава без изменения данных."""

    document_id: UUID
