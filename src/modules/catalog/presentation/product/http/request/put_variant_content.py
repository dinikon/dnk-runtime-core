from pydantic import BaseModel, ConfigDict


class PutVariantContentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    short_description: str
