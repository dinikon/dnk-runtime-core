from pydantic import BaseModel, ConfigDict
from uuid import UUID


class CreateCatalogCategoryRequest(BaseModel):
    """Принимает название на выбранном языке и положение новой категории."""

    model_config = ConfigDict(extra="forbid")
    parent_id: UUID | None = None
    locale: str
    name: str
