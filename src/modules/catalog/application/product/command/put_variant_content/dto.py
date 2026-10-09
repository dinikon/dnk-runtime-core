from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class PutVariantContentResultDTO:
    """Результат конкретного сценария put_variant_content."""

    id: UUID
    revision: int
