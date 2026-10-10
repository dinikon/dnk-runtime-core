from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class PutTagTranslationResultDTO:
    """Подтверждённый результат конкретного сценария put_tag_translation."""

    id: UUID
    revision: int
