from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ReplaceVariantsResultDTO:
    """Собственный результат сценария replace_variants."""

    id: UUID
    revision: int
