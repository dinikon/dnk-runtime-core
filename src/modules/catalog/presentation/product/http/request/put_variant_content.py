from pydantic import BaseModel, ConfigDict


class PutVariantContentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    schema_version: int
    blocks: dict[str, str]
