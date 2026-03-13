from uuid import UUID

from pydantic import BaseModel


class DeleteCrmItemResponseSchema(BaseModel):
    item_id: UUID
    ok: bool
