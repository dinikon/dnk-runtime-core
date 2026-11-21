from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ConfirmReturnDocumentCommand:
    """Передаёт намерение и версию сохранённого плана возврата."""

    document_id: UUID
    expected_version: int
