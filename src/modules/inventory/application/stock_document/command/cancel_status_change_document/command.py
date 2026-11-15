from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CancelStatusChangeDocumentCommand:
    """Передаёт намерение и версию сохранённого плана изменения состояния."""

    document_id: UUID
    expected_version: int
