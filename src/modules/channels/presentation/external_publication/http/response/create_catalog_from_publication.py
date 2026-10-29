from uuid import UUID
from pydantic import BaseModel


class CreateCatalogFromPublicationResponse(BaseModel):
    """Результат одного нажатия без сохранённой операции или черновика."""

    catalog_item_id: UUID
    binding_group_id: UUID
    created: bool
    warnings: tuple[str, ...]
