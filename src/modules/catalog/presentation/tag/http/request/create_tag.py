from pydantic import BaseModel, ConfigDict, Field
from uuid import UUID


class CreateTagRequest(BaseModel):
    """Отдельное тело сценария create_tag."""

    model_config = ConfigDict(extra="forbid")
    locale: str = Field(min_length=2, max_length=64)
    label: str = Field(min_length=1, max_length=255)
