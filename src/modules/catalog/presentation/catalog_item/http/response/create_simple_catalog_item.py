from pydantic import BaseModel
from uuid import UUID


class CreateSimpleCatalogItemResponse(BaseModel):
    """HTTP результат отдельного сценария create_simple_catalog_item."""

    id: UUID
    root_revision: int
    child_ids: tuple[UUID, ...]
