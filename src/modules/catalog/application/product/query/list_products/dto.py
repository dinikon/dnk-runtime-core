from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ProductListItemDTO:
    """Одна строка товара, независимо от числа принадлежащих позиций."""

    id: UUID
    kind: str
    product_type_id: UUID
    revision: int
    schema_version: int
    content: dict[str, str] | None
    locales: tuple[str, ...]
    title: str | None
    variant_count: int


@dataclass(frozen=True, slots=True)
class ListProductsPageDTO:
    """Страница результата list_products без повторов Product."""

    items: tuple[ProductListItemDTO, ...]
    total: int
    page: int
    page_size: int
