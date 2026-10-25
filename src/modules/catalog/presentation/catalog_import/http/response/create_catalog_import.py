from uuid import UUID
from pydantic import BaseModel


class CreateCatalogImportResponse(BaseModel):
    """HTTP-результат create_catalog_import."""

    id: UUID
    status: str
