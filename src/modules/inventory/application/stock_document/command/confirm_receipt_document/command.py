from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ConfirmReceiptDocumentCommand:
    """Передаёт намерение и версию сохранённого плана поступления."""

    document_id: UUID
    expected_version: int
