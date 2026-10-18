from pydantic import BaseModel, ConfigDict, Field


class WooReadExtension(BaseModel):
    """Ограничивает extension Woo, не сохраняя произвольные meta_data и секреты."""

    model_config = ConfigDict(extra="forbid")
    parent_id: int | None = None
    product_type: str | None = Field(default=None, max_length=100)
    status: str | None = Field(default=None, max_length=100)
    description: str | None = Field(default=None, max_length=300000)
    sale_start_gmt: str | None = Field(default=None, max_length=100)
    sale_end_gmt: str | None = Field(default=None, max_length=100)
