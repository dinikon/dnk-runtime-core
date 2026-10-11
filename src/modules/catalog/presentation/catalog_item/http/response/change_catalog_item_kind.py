from pydantic import BaseModel
from uuid import UUID


class ChangeCatalogItemKindResponse(BaseModel):
    """HTTP результат отдельного сценария change_catalog_item_kind."""

    item_id: UUID
    root_id: UUID
    item_revision: int
    root_revision: int
    child_ids: tuple[UUID, ...]
