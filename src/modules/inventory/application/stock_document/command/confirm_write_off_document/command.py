from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ConfirmWriteOffDocumentCommand:
    """Передаёт намерение и версию сохранённого плана списания."""

    document_id: UUID
    expected_version: int
