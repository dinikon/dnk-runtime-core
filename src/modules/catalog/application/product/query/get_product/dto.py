from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class GetProductDetailsDTO:
    """Результат конкретного сценария get_product."""

    id: UUID
    kind: str
    product_type_id: UUID
    revision: int
    schema_version: int
    content: dict[str, str] | None
    locales: tuple[str, ...]
    variant_id: UUID
    virtual: bool
    downloadable: bool
    variant_content: dict[str, str] | None
    variant_locales: tuple[str, ...]
