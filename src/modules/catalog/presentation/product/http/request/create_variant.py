from uuid import UUID
from pydantic import BaseModel, ConfigDict


class CreateVariantRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sku_id: UUID
