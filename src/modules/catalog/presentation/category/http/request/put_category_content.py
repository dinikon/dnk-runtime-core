from pydantic import BaseModel, ConfigDict, Field


class PutCategoryContentRequest(BaseModel):
    """Отдельное тело HTTP-сценария put_category_content."""

    model_config = ConfigDict(extra="forbid")

    label: str = Field(min_length=1, max_length=255)
