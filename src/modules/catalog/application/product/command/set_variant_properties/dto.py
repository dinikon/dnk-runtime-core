from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class SetVariantPropertiesResultDTO:
    """Результат конкретного сценария set_variant_properties."""

    id: UUID
    revision: int
