from dataclasses import dataclass, field
from src.modules.channels.domain.external_publication.value_object.core import JsonValue
from uuid import UUID
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class CatalogDraftImageDTO:
    """Передаёт подготовленный сервером файл для общей операции Catalog."""

    image_id: str
    file_id: UUID
    alt: str = ""


@dataclass(frozen=True, slots=True)
class CatalogDraftValuesDTO:
    """Содержит только подтверждаемые поля переноса, без внешнего native JSON."""

    titles: dict[str, str]
    sku: str | None
    regular_price: Decimal | None
    sale_price: Decimal | None
    currency: str | None
    manage_stock: bool
    quantity: Decimal | None
    stock_status: str | None
    backorders: str
    descriptions: dict[str, str] = field(default_factory=dict)
    gallery: tuple[str, ...] = ()
    primary_image_id: str | None = None
    image_files: tuple[CatalogDraftImageDTO, ...] = ()


@dataclass(frozen=True, slots=True)
class CatalogDraftCheckDTO:
    """Сообщает ошибки владельца значений и вычисленное целевое наличие."""

    issues: tuple[tuple[str, str], ...]
    stock_status: str | None


@dataclass(frozen=True, slots=True)
class PublicationCatalogSourceDTO:
    """Передаёт локальный observed snapshot для preview и проверки команды."""

    publication_id: UUID
    connection_id: UUID
    channel_id: UUID
    archived: bool
    observed_revision: int
    title: str | None
    title_locale: str | None
    external_sku: str | None
    price: Decimal | None
    sale_price: Decimal | None
    currency: str | None
    quantity: Decimal | None
    stock_status: str
    warnings: tuple[str, ...]
    main_image_url: str | None
    resource_type: str = "product"
    external_id: str = ""
    provider_context: dict[str, JsonValue] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class CatalogBindingDTO:
    """Описывает конкретную активную либо историческую связь без агрегата."""

    binding_id: UUID
    representation_id: UUID
    connection_id: UUID
    publication_id: UUID
    catalog_item_id: UUID
    revision: int
    active: bool


@dataclass(frozen=True, slots=True)
class CatalogCandidateDTO:
    """Передаёт строку выбора товара от публичного фасада Catalog."""

    id: UUID
    title: str | None
    sku: str | None
    status: str


@dataclass(frozen=True, slots=True)
class CatalogCandidatesDTO:
    """Возвращает страницу публичного поиска без SQL-моделей другого контекста."""

    items: tuple[CatalogCandidateDTO, ...]
    total: int


@dataclass(frozen=True, slots=True)
class CatalogCreationReceiptDTO:
    """Фиксирует завершённый результат одного пользовательского намерения."""

    request_key: UUID
    publication_id: UUID
    input_hash: str
    observed_revision: int
    catalog_item_id: UUID
    representation_id: UUID
    binding_id: UUID
