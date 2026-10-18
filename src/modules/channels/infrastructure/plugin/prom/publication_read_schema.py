from pydantic import BaseModel, ConfigDict, Field


class PromReadExtension(BaseModel):
    """Ограничивает read extension безопасными несекретными полями Prom."""

    model_config = ConfigDict(extra="forbid")
    status: str | None = Field(default=None, max_length=100)
    group_id: int | None = None
    provider_external_id: str | None = Field(default=None, max_length=512)
    description: str | None = Field(default=None, max_length=300000)
    discount: dict[str, str | None] | None = None
