from uuid import UUID

from pydantic import BaseModel


class DeleteContactResponseSchema(BaseModel):
    id: UUID
    ok: bool
