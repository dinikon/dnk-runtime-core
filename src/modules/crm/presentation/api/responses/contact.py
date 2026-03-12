from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict


class GetContactResponseSchema(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: UUID
    first_name: str
    last_name: str | None
    middle_name: str | None
