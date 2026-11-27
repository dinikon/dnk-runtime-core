from typing import Annotated
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field
from src.modules.feed_builder.presentation.feed.http.schema.graph import FieldNodeSchema


class PreviewFieldCalculationRequest(BaseModel):
    """Принимает выбор позиции и несохранённое определение без цен клиента или времени."""

    model_config = ConfigDict(extra="forbid", strict=True)
    expected_version: int = Field(ge=1, le=9223372036854775807)
    field_id: Annotated[UUID, Field(strict=False)]
    catalog_item_id: Annotated[UUID, Field(strict=False)]
    catalog_variant_id: Annotated[UUID, Field(strict=False)] | None = None
    definition_override: FieldNodeSchema | None = None
