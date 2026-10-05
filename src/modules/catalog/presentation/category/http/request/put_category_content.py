from pydantic import BaseModel, ConfigDict


class PutCategoryContentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    name: str
