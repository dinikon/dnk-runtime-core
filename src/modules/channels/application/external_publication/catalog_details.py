from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from uuid import UUID
from src.modules.channels.domain.channel.value_object.connection_config import (
    ConnectionConfigVO,
)
from src.modules.channels.domain.types import JsonObject


@dataclass(frozen=True, slots=True)
class PublicationLookup:
    """Идентификаторы локальной позиции и нативного источника."""

    id: UUID
    resource_type: str
    external_id: str
    kind: str
    parent_id: UUID | None
    revision: int
    platform_data: JsonObject


@dataclass(frozen=True, slots=True)
class PublicationCreationSnapshot:
    """Неизменный доступ и состав семьи на момент запроса."""

    connection_id: UUID
    platform: str
    config: ConnectionConfigVO
    config_revision: int
    encrypted_credentials: bytes = field(repr=False)
    root_id: UUID
    publications: tuple[PublicationLookup, ...]


@dataclass(frozen=True, slots=True)
class PublicationTranslationDetails:
    """Реально полученный контент одной локали."""

    locale: str
    title: str | None
    body: str | None


@dataclass(frozen=True, slots=True)
class PublicationProductDetails:
    """Поддерживаемые Catalog значения без нативной модели платформы."""

    resource_type: str
    external_id: str
    parent_external_id: str | None
    kind: str
    sku: str | None
    translations: tuple[PublicationTranslationDetails, ...]
    image_urls: tuple[str, ...]
    manage_stock: bool
    quantity: Decimal | None
    stock_status: str | None
    backorders: str = "no"
    virtual: bool = False
    weight: Decimal | None = None
    weight_unit: str | None = None
    length: Decimal | None = None
    width: Decimal | None = None
    height: Decimal | None = None
    dimension_unit: str | None = None
    regular_price: Decimal | None = None
    currency: str | None = None
    sale_price: Decimal | None = None
    date_on_sale_from: datetime | None = None
    date_on_sale_to: datetime | None = None


@dataclass(frozen=True, slots=True)
class PublicationDetails:
    """Полная известная семья, полученная непосредственно через API площадки."""

    products: tuple[PublicationProductDetails, ...]
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class CreatedPublicationCatalog:
    """Результат владельца Catalog и порядок продаваемых позиций."""

    root_id: UUID
    position_ids: tuple[UUID, ...]
    warnings: tuple[str, ...]
