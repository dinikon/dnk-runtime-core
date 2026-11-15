from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class PrepareReceiptQuery:
    """Передаёт документ для подготовки фактического состава без изменения данных."""

    document_id: UUID
