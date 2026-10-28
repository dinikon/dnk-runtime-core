from uuid import UUID
from pydantic import BaseModel


class UpdateCatalogVariantResponse(BaseModel):
    """Отдельное HTTP-подтверждение изменения товара."""

    id: UUID
