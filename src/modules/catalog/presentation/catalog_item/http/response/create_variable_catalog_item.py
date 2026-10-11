from pydantic import BaseModel
from uuid import UUID


class CreateVariableCatalogItemResponse(BaseModel):
    """HTTP результат отдельного сценария create_variable_catalog_item."""

    id: UUID
    root_revision: int
    child_ids: tuple[UUID, ...]
