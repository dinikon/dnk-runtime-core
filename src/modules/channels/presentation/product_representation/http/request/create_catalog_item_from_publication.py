from uuid import UUID
from typing import Literal, Annotated
from pydantic import BaseModel, ConfigDict, Field


class CreateCatalogItemFromPublicationValuesRequest(BaseModel):
    """Принимает только поля подтверждённого переноса без статуса и metadata."""

    model_config = ConfigDict(extra="forbid")
    titles: dict[
        Annotated[str, Field(min_length=1, max_length=35)],
        Annotated[str, Field(max_length=2000)],
    ] = Field(min_length=1, max_length=2)
    descriptions: dict[
        Annotated[str, Field(min_length=1, max_length=35)],
        Annotated[str, Field(max_length=300000)],
    ] = Field(default_factory=dict, max_length=2)
    gallery: list[Annotated[str, Field(min_length=1, max_length=200)]] = Field(
        default_factory=list, max_length=100
    )
    primary_image_id: str | None = Field(default=None, max_length=200)
    sku: str | None = Field(default=None, max_length=128)
    regular_price: str | None = Field(
        default=None, max_length=64, pattern=r"^-?\d{1,40}(?:\.\d{1,20})?$"
    )
    sale_price: str | None = Field(
        default=None, max_length=64, pattern=r"^-?\d{1,40}(?:\.\d{1,20})?$"
    )
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    manage_stock: bool
    quantity: str | None = Field(
        default=None, max_length=40, pattern=r"^-?\d{1,20}(?:\.\d{1,12})?$"
    )
    stock_status: Literal["in_stock", "out_of_stock", "on_backorder"] | None = None
    backorders: Literal["no", "notify", "yes"] = "no"


class CreateCatalogItemFromPublicationRequest(BaseModel):
    """Фиксирует пользовательский intent, snapshot и подтверждённые значения."""

    model_config = ConfigDict(extra="forbid")
    preparation_id: UUID | None = None
    expected_preparation_revision: int | None = Field(default=None, ge=1)
    request_key: UUID
    expected_observed_revision: int = Field(ge=1)
    values: CreateCatalogItemFromPublicationValuesRequest
