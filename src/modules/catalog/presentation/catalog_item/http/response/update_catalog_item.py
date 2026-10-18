from uuid import UUID
from pydantic import BaseModel


class UpdateCatalogItemResponse(BaseModel):
    """Отдельное HTTP-подтверждение изменения товара."""

    id: UUID
