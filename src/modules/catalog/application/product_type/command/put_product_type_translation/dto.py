from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class PutProductTypeTranslationResultDTO:
    """Результат конкретного сценария put_product_type_translation."""

    id: UUID
    revision: int
