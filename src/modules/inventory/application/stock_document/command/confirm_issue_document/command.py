from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ConfirmIssueDocumentCommand:
    """Передаёт намерение и версию сохранённого плана расхода."""

    document_id: UUID
    expected_version: int
