from uuid import UUID
from datetime import datetime
from pydantic import BaseModel


class PublicationImportImageResponse(BaseModel):
    """Описывает доступное фото без раскрытия внешнего адреса или file_id."""

    id: str
    preview_url: str | None
    alt: str
    error_code: str | None


class PublicationImportValuesResponse(BaseModel):
    """Передаёт редактируемые поля будущего товара с точными decimal строками."""

    titles: dict[str, str]
    descriptions: dict[str, str]
    sku: str | None
    regular_price: str | None
    sale_price: str | None
    currency: str | None
    manage_stock: bool
    quantity: str | None
    stock_status: str | None
    backorders: str
    gallery: list[str]
    primary_image_id: str | None


class GetPublicationImportResponse(BaseModel):
    """Возвращает этапы подготовки и содержимое предпросмотра."""

    preparation_id: UUID
    publication_id: UUID
    status: str
    revision: int
    observed_revision: int
    read_at: datetime | None
    created_at: datetime
    expires_at: datetime
    error_code: str | None
    values: PublicationImportValuesResponse | None
    translations: dict[str, dict[str, str | None]]
    images: list[PublicationImportImageResponse]
    warnings: list[str]
