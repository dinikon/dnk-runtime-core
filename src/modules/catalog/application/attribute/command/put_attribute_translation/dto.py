from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class PutAttributeTranslationResultDTO:
    """Подтверждённый результат конкретного сценария put_attribute_translation."""

    id: UUID
    revision: int
