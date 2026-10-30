from uuid import UUID

from pydantic import BaseModel


class RefreshPublicationStockResponse(BaseModel):
    """Принятые операции refresh_publication_stock."""

    operation_ids: tuple[UUID, ...]
