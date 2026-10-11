from pydantic import BaseModel
from uuid import UUID


class ReplaceCatalogItemStructureResponse(BaseModel):
    """HTTP результат отдельного сценария replace_catalog_item_structure."""

    item_id: UUID
    root_id: UUID
    item_revision: int
    root_revision: int
    child_ids: tuple[UUID, ...]
