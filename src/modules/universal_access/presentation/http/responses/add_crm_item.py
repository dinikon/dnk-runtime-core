from uuid import UUID

from pydantic import BaseModel


class AddCrmItemResponseSchema(BaseModel):
    item_id: UUID
    result: dict[str, str]
