from uuid import UUID
from pydantic import BaseModel


class CancelCatalogImportResponse(BaseModel):
    """HTTP-результат cancel_catalog_import."""

    id: UUID
    status: str
