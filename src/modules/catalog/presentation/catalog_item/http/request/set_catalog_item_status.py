from pydantic import BaseModel, ConfigDict, Field
from typing import Literal


class SetCatalogItemStatusRequest(BaseModel):
    """Отдельное тело команды set_catalog_item_status."""

    model_config = ConfigDict(extra="forbid")
    expected_revision: int = Field(ge=1)
    status: Literal["draft", "active", "archived"]
