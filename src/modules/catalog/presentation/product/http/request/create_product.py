from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CreateProductContentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    locale: str
    blocks: dict[str, str]


class CreateProductRequest(BaseModel):
    """Создание SIMPLE без клиентских ID, tenant и аудита."""

    model_config = ConfigDict(extra="forbid", strict=True)

    sku_id: UUID = Field(strict=False)
    contents: list[CreateProductContentRequest] = Field(default_factory=list)
    product_type_id: UUID | None = None
    schema_version: int | None = None
