from uuid import UUID
from pydantic import BaseModel, ConfigDict


class PutVariantRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sku_id: UUID
