from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CreateProductContentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    locale: str
    name: str
    description: str | None = None


class CreateProductRequest(BaseModel):
    """Создание SIMPLE без клиентских ID, tenant и аудита."""

    model_config = ConfigDict(extra="forbid", strict=True)

    sku_id: UUID = Field(strict=False)
    contents: list[CreateProductContentRequest] = Field(default_factory=list)
