from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ReplaceAttributeOptionsResultDTO:
    """Подтверждённый результат конкретного сценария replace_attribute_options."""

    id: UUID
    revision: int
