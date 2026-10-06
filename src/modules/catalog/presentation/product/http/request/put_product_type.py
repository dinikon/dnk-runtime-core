from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PutProductTypeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    product_type_id: UUID = Field(strict=False)
    expected_schema_version: int
