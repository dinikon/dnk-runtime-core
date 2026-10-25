from uuid import UUID
from pydantic import BaseModel


class ConfigureCatalogImportResponse(BaseModel):
    """HTTP-результат configure_catalog_import."""

    id: UUID
    version: int
    status: str
