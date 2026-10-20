from decimal import Decimal
from pydantic import BaseModel


class PreviewCatalogDraftValuesResponse(BaseModel):
    """Описывает предложенные точные значения, не HTTP-вход команды."""

    titles: dict[str, str]
    sku: str | None
    regular_price: Decimal | None
    sale_price: Decimal | None
    currency: str | None
    manage_stock: bool
    quantity: Decimal | None
    stock_status: str | None
    backorders: str


class PreviewCatalogDraftIssueResponse(BaseModel):
    """Связывает безопасное пояснение владельца с полем формы."""

    field: str
    message: str


class PreviewCatalogDraftResponse(BaseModel):
    """Возвращает предложение и объяснения без создания товара."""

    observed_revision: int
    values: PreviewCatalogDraftValuesResponse
    issues: tuple[PreviewCatalogDraftIssueResponse, ...]
    warnings: tuple[str, ...]
    main_image_url: str | None
    origins: dict[str, str]
