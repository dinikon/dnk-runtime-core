from uuid import UUID

from pydantic import BaseModel


class UpdateCrmItemResponseSchema(BaseModel):
    item_id: UUID
    result: dict[str, str]
