from pydantic import BaseModel, ConfigDict, Field


class CreateAttributeOptionRequest(BaseModel):
    """Значение enum в конкретном HTTP-сценарии create_attribute."""

    model_config = ConfigDict(extra="forbid")
    code: str = Field(min_length=1, max_length=64)
    label: str = Field(min_length=1, max_length=255)


class CreateAttributeRequest(BaseModel):
    """Отдельное тело HTTP-сценария create_attribute."""

    model_config = ConfigDict(extra="forbid")
    code: str = Field(min_length=1, max_length=64)
    locale: str = Field(min_length=2, max_length=64)
    label: str = Field(min_length=1, max_length=255)
    options: tuple[CreateAttributeOptionRequest, ...] = ()
