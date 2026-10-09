from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ProductListItemDTO:
    """Строка списка конкретного сценария без доменного поведения."""

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


@dataclass(frozen=True, slots=True)
class ListProductsPageDTO:
    """Результат конкретного сценария list_products."""

    items: tuple[ProductListItemDTO, ...]
    total: int
    page: int
    page_size: int
