from pydantic import BaseModel


class GetCrmItemResponseSchema(BaseModel):
    result: dict[str, str]
