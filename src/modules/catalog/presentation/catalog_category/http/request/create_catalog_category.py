from pydantic import BaseModel, ConfigDict
from uuid import UUID


class CreateCatalogCategoryRequest(BaseModel):
    """Принимает исходное название и положение новой категории."""

    model_config = ConfigDict(extra="forbid")
    parent_id: UUID | None = None
    source_locale: str
    name: str
