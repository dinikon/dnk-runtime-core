from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ProductTypeListBlockDTO:
    """Блок схемы в результате list_product_types."""

    block_id: UUID
    code: str
    value_type: str
    label: str | None
    scope: str
    required: bool
    position: int


@dataclass(frozen=True, slots=True)
class ProductTypeListItemDTO:
    """Строка списка конкретного сценария без доменного поведения."""

    id: UUID
    code: str
    is_system: bool
    revision: int
    label: str | None
    locales: tuple[str, ...]
    schema_version: int
    blocks: tuple[ProductTypeListBlockDTO, ...]


@dataclass(frozen=True, slots=True)
class ListProductTypesPageDTO:
    """Результат конкретного сценария list_product_types."""

    items: tuple[ProductTypeListItemDTO, ...]
    total: int
    page: int
    page_size: int
