from pydantic import BaseModel, ConfigDict, Field


class PromReadExtension(BaseModel):
    """Ограничивает provider metadata безопасными несекретными полями Prom."""

    model_config = ConfigDict(extra="forbid")
    status: str | None = Field(default=None, max_length=100)
    group_id: int | None = None
    import_key: str | None = Field(default=None, max_length=512)
    description: str | None = Field(default=None, max_length=300000)
    discount: dict[str, str | None] | None = None
