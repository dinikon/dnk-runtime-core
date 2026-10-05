from pydantic import BaseModel, ConfigDict, Field


class AttributeContentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    locale: str
    name: str


class AttributeOptionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    code: str
    contents: list[AttributeContentRequest] = Field(default_factory=list)


class CreateAttributeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    code: str
    options: list[AttributeOptionRequest] = Field(min_length=1)
    contents: list[AttributeContentRequest] = Field(default_factory=list)
