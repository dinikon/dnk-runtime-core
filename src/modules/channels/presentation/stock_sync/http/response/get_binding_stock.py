from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class StockOperationFields(BaseModel):
    """Только безопасные результаты Worker, без нативных документов."""

    publication_id: UUID
    operation_id: UUID
    direction: str
    status: str
    quantity: str | None
    availability: str | None
    observed_at: datetime | None
    desired_quantity: int | None
    error_code: str | None
    updated_at: datetime
    recovery_required: bool


class BindingStockItemFields(BaseModel):
    """Количество и владельцы двух сторон явной пары."""

    publication_id: UUID
    stock_owner_id: UUID
    catalog_position_id: UUID
    catalog_owner_id: UUID
    catalog_quantity: int | None
    publication_quantity: str | None
    publication_availability: str | None
    export_blocker: str | None
    operation: StockOperationFields | None


class GetBindingStockResponse(BaseModel):
    """Состояние существующей группы из локального хранения."""

    allow_stock_export: bool
    items: tuple[BindingStockItemFields, ...]
