from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class GetProductTypeBlockDTO:
    """Блок схемы в результате get_product_type."""

    block_id: UUID
    code: str
    value_type: str
    label: str | None
    scope: str
    required: bool
    position: int


@dataclass(frozen=True, slots=True)
class GetProductTypeDetailsDTO:
    """Результат конкретного сценария get_product_type."""

    id: UUID
    code: str
    is_system: bool
    revision: int
    label: str | None
    locales: tuple[str, ...]
    schema_version: int
    blocks: tuple[GetProductTypeBlockDTO, ...]
