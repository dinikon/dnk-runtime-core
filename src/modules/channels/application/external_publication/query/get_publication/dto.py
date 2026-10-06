from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True, slots=True)
class PublicationImageDTO:
    """Передаёт изображение карточки для сценария чтения деталей."""

    url: str
    alt: str


@dataclass(frozen=True, slots=True)
class PublicationCategoryDTO:
    """Передаёт внешнюю категорию карточки."""

    external_id: str
    name: str


@dataclass(frozen=True, slots=True)
class PublicationAttributeDTO:
    """Передаёт пару имени и значения характеристики."""

    name: str
    value: str
    unit: str | None


@dataclass(frozen=True, slots=True)
class PublicationVariantDTO:
    """Передаёт позицию вариации внутри читаемой карточки."""

    id: UUID
    external_id: str
    title: str | None
    sku: str | None
    price: Decimal | None
    currency: str | None
    quantity: Decimal | None
    availability: str | None
    source_status: str | None
    attributes: tuple[PublicationAttributeDTO, ...]


@dataclass(frozen=True, slots=True)
class PublicationDetailsDTO:
    """Передаёт поля сохранённой карточки и её вариации без native JSON."""

    id: UUID
    channel_id: UUID
    external_id: str
    resource_type: str
    title: str | None
    sku: str | None
    external_url: str | None
    description_html: str | None
    short_description_html: str | None
    price: Decimal | None
    regular_price: Decimal | None
    sale_price: Decimal | None
    currency: str | None
    quantity: Decimal | None
    availability: str | None
    source_status: str | None
    product_type: str | None
    images: tuple[PublicationImageDTO, ...]
    categories: tuple[PublicationCategoryDTO, ...]
    attributes: tuple[PublicationAttributeDTO, ...]
    variants: tuple[PublicationVariantDTO, ...]
    expected_variations: int | None
    warnings: tuple[str, ...]
    schema_version: int
    revision: int
    observed_at: datetime
