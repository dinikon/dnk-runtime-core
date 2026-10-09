from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class GetVariantDetailsDTO:
    """Результат конкретного сценария get_variant."""

    id: UUID
    product_id: UUID
    revision: int
    schema_version: int
    content: dict[str, str] | None
    locales: tuple[str, ...]
    virtual: bool
    downloadable: bool
