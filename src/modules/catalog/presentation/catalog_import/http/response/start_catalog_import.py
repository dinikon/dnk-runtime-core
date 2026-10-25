from uuid import UUID
from pydantic import BaseModel


class StartCatalogImportResponse(BaseModel):
    """HTTP-результат start_catalog_import."""

    id: UUID
    status: str
