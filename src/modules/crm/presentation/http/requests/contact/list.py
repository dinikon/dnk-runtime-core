from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class ListContactsRequestSchema(BaseModel):
    ids: list[UUID] = Field(default_factory=list)
    first_name: str | None = None
    last_name: str | None = None
    middle_name: str | None = None
    sort_field: Literal[
        "created_at",
        "updated_at",
        "first_name",
        "last_name",
        "middle_name",
    ] = "created_at"
    sort_direction: Literal["asc", "desc"] = "desc"
    limit: int = 50
    offset: int = 0
